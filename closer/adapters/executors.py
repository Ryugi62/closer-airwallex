"""Executors: AUTO_ADJUST writes a journal line; an approved refund moves money through the gateway."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Protocol

from closer.domain.decision import Decision
from closer.domain.models import Action


class TransferGateway(Protocol):
    def create_transfer(self, idempotency_key: str, beneficiary_id: str, amount: Decimal, currency: str, reason: str) -> str: ...


class FakeTransferGateway:
    """Offline stand-in for the Airwallex transfer endpoint. Outputs are labelled FAKE."""

    def __init__(self) -> None:
        self.sent: List[dict] = []

    def create_transfer(self, idempotency_key: str, beneficiary_id: str, amount: Decimal, currency: str, reason: str) -> str:
        if any(s["request_id"] == idempotency_key for s in self.sent):
            return next(s["id"] for s in self.sent if s["request_id"] == idempotency_key)
        tid = "FAKE-TR-%d" % (len(self.sent) + 1)
        self.sent.append({"id": tid, "request_id": idempotency_key, "beneficiary_id": beneficiary_id,
                          "amount": str(amount), "currency": currency, "reason": reason})
        return tid


class RoutingExecutor:
    def __init__(self, gateway: TransferGateway, beneficiaries: Dict[str, str]) -> None:
        self.gateway = gateway
        self.beneficiaries = beneficiaries
        self.journal: List[dict] = []

    def execute(self, decision: Decision) -> str:
        if decision.action == Action.AUTO_ADJUST:
            ref = "JRN-%d" % (len(self.journal) + 1)
            self.journal.append({"ref": ref, "rule": decision.rule_id, "invoice": decision.finding.invoice_id,
                                 "amount": str(decision.amount), "currency": decision.currency,
                                 "kind": decision.finding.mismatch.value, "evidence": list(decision.finding.txn_ids)})
            return ref
        if decision.action == Action.HOLD_FOR_APPROVAL:
            benef = self.beneficiaries[decision.counterparty]
            return self.gateway.create_transfer(decision.idempotency_key, benef, decision.amount,
                                                decision.currency, "refund duplicate payment " + (decision.finding.invoice_id or ""))
        raise ValueError("not executable: %s" % decision.action)
