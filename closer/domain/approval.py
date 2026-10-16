"""An approval is valid only for the exact card it was produced for."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Tuple


@dataclass(frozen=True)
class ApprovalCard:
    action: str
    invoice_id: str
    amount: Decimal
    currency: str
    counterparty: str
    evidence_txn_ids: Tuple[str, ...]

    def digest(self) -> str:
        body = json.dumps({
            "action": self.action, "invoice_id": self.invoice_id,
            "amount": "%.4f" % self.amount, "currency": self.currency,
            "counterparty": self.counterparty, "evidence": list(self.evidence_txn_ids),
        }, sort_keys=True)
        return hashlib.sha256(body.encode()).hexdigest()


@dataclass(frozen=True)
class Approval:
    card_digest: str
    approver: str


def approve(card: ApprovalCard, approver: str) -> Approval:
    return Approval(card_digest=card.digest(), approver=approver)


def verify(card: ApprovalCard, approval: Approval) -> bool:
    return approval.card_digest == card.digest()
