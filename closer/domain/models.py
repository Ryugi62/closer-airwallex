"""Domain vocabulary. Pure Python: no I/O, no frameworks."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional, Tuple


class Direction(str, Enum):
    IN = "IN"
    OUT = "OUT"


class MismatchType(str, Enum):
    MATCHED = "MATCHED"
    NOT_DUE = "NOT_DUE"
    NOT_SETTLED = "NOT_SETTLED"
    FEE_DEDUCTED = "FEE_DEDUCTED"
    FX_DIFFERENCE = "FX_DIFFERENCE"
    DUPLICATE_PAYMENT = "DUPLICATE_PAYMENT"
    MISSING_PAYMENT = "MISSING_PAYMENT"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    UNMATCHED_TXN = "UNMATCHED_TXN"


NON_MISMATCH = (MismatchType.MATCHED, MismatchType.NOT_DUE, MismatchType.NOT_SETTLED)


class Action(str, Enum):
    NONE = "NONE"
    AUTO_ADJUST = "AUTO_ADJUST"
    HOLD_FOR_APPROVAL = "HOLD_FOR_APPROVAL"
    ESCALATE = "ESCALATE"


class Link(str, Enum):
    REFERENCE = "REFERENCE"
    INFERRED = "INFERRED"


@dataclass(frozen=True)
class Invoice:
    id: str
    direction: Direction
    counterparty: str
    currency: str
    amount: Decimal
    due_date: date
    settlement_currency: Optional[str] = None
    quoted_rate: Optional[Decimal] = None

    @property
    def fx(self) -> bool:
        return bool(self.settlement_currency and self.quoted_rate)

    @property
    def expected_amount(self) -> Decimal:
        return self.amount * self.quoted_rate if self.fx else self.amount

    @property
    def expected_currency(self) -> str:
        return self.settlement_currency if self.fx else self.currency


@dataclass(frozen=True)
class BankTxn:
    id: str
    currency: str
    amount: Decimal
    fee: Decimal
    net: Decimal
    status: str
    description: str
    created_at: str

    @property
    def settled(self) -> bool:
        return self.status == "SETTLED"

    @property
    def in_transit(self) -> bool:
        return self.status in ("PENDING", "PROCESSING")


@dataclass(frozen=True)
class Finding:
    invoice_id: Optional[str]
    mismatch: MismatchType
    txn_ids: Tuple[str, ...]
    link: Optional[Link]
    diff: Decimal
    currency: str
    drift_pct: Optional[Decimal] = None
    paid_currency: Optional[str] = None


@dataclass(frozen=True)
class AuditEntry:
    cycle_id: str
    subject_id: str
    mismatch: str
    rule_id: str
    evidence_txn_ids: Tuple[str, ...]
    action: str
    outcome: str
    amount: str
    currency: str
    explanation: str
