import json
from decimal import Decimal as D

from closer.adapters.airwallex_http import AirwallexGateway

LOGIN = (201, {}, json.dumps({"token": "T0K", "expires_at": "2099-01-01T00:00:00+0000"}))


class FakeTransport:
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def __call__(self, method, path, headers, body):
        self.calls.append((method, path, dict(headers), body))
        key = (method, path.split("?")[0])
        if key == ("POST", "/api/v1/authentication/login"):
            return LOGIN
        status, hdr, payload = self.routes[key]
        return status, hdr, json.dumps(payload)


FTX = {"items": [{"id": "ftx_1", "currency": "USD", "amount": 100, "fee": 1.5, "net": 98.5, "status": "SETTLED",
                  "description": "INV-1", "created_at": "2026-10-13T00:00:00+00:00"}], "has_more": False}


def gw(extra=None):
    routes = {("GET", "/api/v1/financial_transactions"): (200, {"x-request-id": "r1"}, FTX)}
    routes.update(extra or {})
    t = FakeTransport(routes)
    return AirwallexGateway(t, client_id="cid", api_key="key"), t


def test_login_headers_and_bearer_token():
    g, t = gw()
    g.list_transactions()
    login = t.calls[0]
    assert login[2]["x-client-id"] == "cid" and login[2]["x-api-key"] == "key"
    assert t.calls[1][2]["Authorization"] == "Bearer T0K"


def test_parses_transactions_to_domain():
    g, _ = gw()
    [x] = g.list_transactions()
    assert (x.id, x.currency, x.amount, x.fee, x.net) == ("ftx_1", "USD", D("100"), D("1.5"), D("98.5"))


def test_token_reused_across_calls():
    g, t = gw()
    g.list_transactions()
    g.list_transactions()
    assert sum(1 for c in t.calls if c[1].endswith("/login")) == 1


def test_call_log_records_status_and_request_id():
    g, _ = gw()
    g.list_transactions()
    row = g.call_log[-1]
    assert row["endpoint"] == "GET /api/v1/financial_transactions" and row["status"] == 200 and row["request_id"] == "r1"


def test_create_transfer_uses_idempotency_key_as_request_id():
    g, t = gw({("POST", "/api/v1/transfers/create"): (201, {"x-request-id": "r2"}, {"id": "tr_1", "status": "PAID"})})
    out = g.create_transfer(idempotency_key="abc123", beneficiary_id="b1", amount=D("12.50"), currency="USD", reason="refund")
    sent = json.loads(t.calls[-1][3])
    assert sent["request_id"] == "abc123" and sent["transfer_amount"] == 12.5 and out == "tr_1"
