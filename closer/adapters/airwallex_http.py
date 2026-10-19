"""Airwallex sandbox gateway. HTTP is injected as a transport so the adapter is testable offline."""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Tuple

from closer.domain.models import BankTxn

Transport = Callable[[str, str, Dict[str, str], Optional[str]], Tuple[int, Dict[str, str], str]]
REQUEST_ID_HEADERS = ("x-request-id", "x-b3-traceid")


class AirwallexError(Exception):
    pass


def _dec(v: Any) -> Decimal:
    return Decimal(str(v if v is not None else 0))


class AirwallexGateway:
    def __init__(self, transport: Transport, client_id: str, api_key: str) -> None:
        self._t = transport
        self._client_id = client_id
        self._api_key = api_key
        self._token: Optional[str] = None
        self.call_log: List[Dict[str, Any]] = []
        self.last_response: Any = None

    # --- transport plumbing -------------------------------------------------
    def _login(self) -> str:
        status, _, body = self._t("POST", "/api/v1/authentication/login",
                                  {"x-client-id": self._client_id, "x-api-key": self._api_key,
                                   "Content-Type": "application/json"}, None)
        if status not in (200, 201):
            raise AirwallexError("login failed: HTTP %s" % status)
        return json.loads(body)["token"]

    def _request(self, method: str, path: str, payload: Optional[dict] = None) -> Any:
        if self._token is None:
            self._token = self._login()
        headers = {"Authorization": "Bearer " + self._token, "Content-Type": "application/json"}
        status, hdr, body = self._t(method, path, headers, json.dumps(payload) if payload is not None else None)
        low = {k.lower(): v for k, v in hdr.items()}
        rid = next((low[h] for h in REQUEST_ID_HEADERS if h in low), None)
        try:
            data = json.loads(body) if body else {}
        except ValueError:
            data = {"_raw": body}
        count = len(data["items"]) if isinstance(data, dict) and "items" in data else (len(data) if isinstance(data, list) else None)
        self.call_log.append({"endpoint": "%s %s" % (method, path.split("?")[0]), "status": status,
                              "request_id": rid, "items": count})
        self.last_response = data
        if status >= 400:
            raise AirwallexError("%s %s -> HTTP %s %s" % (method, path, status, body[:500]))
        return data

    # --- reads --------------------------------------------------------------
    def list_transactions(self, page_size: int = 100, max_pages: int = 50) -> List[BankTxn]:
        out: List[BankTxn] = []
        for page in range(max_pages):
            data = self._request("GET", "/api/v1/financial_transactions?page_num=%d&page_size=%d" % (page, page_size))
            for it in data.get("items", []):
                out.append(BankTxn(id=it["id"], currency=it["currency"], amount=_dec(it["amount"]),
                                   fee=_dec(it.get("fee")), net=_dec(it.get("net", it["amount"])),
                                   status=it.get("status", ""), description=it.get("description") or "",
                                   created_at=it.get("created_at", "")))
            if not data.get("has_more"):
                break
        return out

    def list_balances(self) -> List[dict]:
        return self._request("GET", "/api/v1/balances/current")

    def list_transfers(self) -> List[dict]:
        return self._request("GET", "/api/v1/transfers?page_num=0&page_size=10").get("items", [])

    def get_transfer(self, transfer_id: str) -> dict:
        return self._request("GET", "/api/v1/transfers/%s" % transfer_id)

    def list_global_accounts(self) -> List[dict]:
        return self._request("GET", "/api/v1/global_accounts").get("items", [])

    def list_beneficiaries(self) -> List[dict]:
        return self._request("GET", "/api/v1/beneficiaries?page_num=0&page_size=10").get("items", [])

    def list_deposits(self) -> List[dict]:
        return self._request("GET", "/api/v1/deposits?page_num=0&page_size=10").get("items", [])

    def list_fx_conversions(self) -> List[dict]:
        return self._request("GET", "/api/v1/fx/conversions?page_num=0&page_size=10").get("items", [])

    def balances_history(self) -> List[dict]:
        return self._request("GET", "/api/v1/balances/history?page_size=10").get("items", [])

    # --- sandbox-only simulation (demo environment): creates one inbound deposit, moves no money out ---
    def simulate_deposit(self, global_account_id: str, amount: str, currency: str, reference: str) -> dict:
        return self._request("POST", "/api/v1/simulation/deposit/create", {
            "global_account_id": global_account_id, "amount": float(Decimal(str(amount))),
            "currency": currency, "payer_name": "Closer Sandbox Customer", "reference": reference})

    # --- sandbox fixture: a company beneficiary with an HKD local account (the sandbox had none) ---
    def create_beneficiary_hkd(self, request_id: str, company_name: str) -> dict:
        return self._request("POST", "/api/v1/beneficiaries/create", {
            "request_id": request_id, "nickname": company_name + " (HKD)", "transfer_methods": ["LOCAL"], "payer_entity_type": "COMPANY",
            "beneficiary": {"entity_type": "COMPANY", "company_name": company_name,
                            "address": {"country_code": "HK", "city": "Hong Kong", "street_address": "1 Queen's Road Central", "postcode": "000000"},
                            "bank_details": {"account_currency": "HKD", "account_name": company_name, "account_number": "123456789012",
                                             "bank_country_code": "HK", "local_clearing_system": "FPS",
                                             "account_routing_type1": "bank_code", "account_routing_value1": "016",
                                             "account_routing_type2": "branch_code", "account_routing_value2": "478"}}})

    # --- write (refund of a held duplicate; idempotency key doubles as request_id) ---
    def create_transfer(self, idempotency_key: str, beneficiary_id: str, amount: Decimal, currency: str, reason: str) -> str:
        data = self._request("POST", "/api/v1/transfers/create", {
            "request_id": idempotency_key, "beneficiary_id": beneficiary_id,
            "source_currency": currency, "transfer_currency": currency, "transfer_method": "LOCAL",
            "transfer_amount": float(amount), "reason": reason, "reference": idempotency_key[:20],
        })
        return data["id"]
