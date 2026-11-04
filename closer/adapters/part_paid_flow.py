"""Part-paid flow: an invoice is paid in two parts; the second part is absent, then in transit, then settled.
Real: the first part's id, currency and amount (from the sandbox read). SYNTHETIC: the invoice, its amount (first + second part) and the second part.
SIMULATED: the second part's status changes, because the sandbox does not produce split payments on demand.
Every frame goes through the real cycle; only the second part changes between frames."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal as D
from typing import List, Sequence

from closer.application.run_cycle import run_cycle
from closer.domain.models import BankTxn, Direction, Invoice
from closer.domain.policy import Policy

from .late_flow import pick_anchor
from .metrics import new_runtime

INVOICE_ID = "SPLIT-1"
ABSENT = "(absent)"
DUE = date(2026, 11, 10)
AS_OF = date(2026, 11, 12)
SYNTHETIC_TXN = BankTxn("syn_split_1", "USD", D("600.00"), D("0"), D("600.00"), "SETTLED",
                        "wire", "2026-11-01T09:00:00+00:00")
SECOND_ID = "syn_split_2"


@dataclass(frozen=True)
class SplitFrame:
    label: str
    changed: str
    first_id: str
    second_status: str
    invoice_amount: str
    rule: str
    action: str
    outcome: str
    state: str
    reason: str


def _first_part(txns: Sequence[BankTxn]) -> BankTxn:
    a = pick_anchor(txns)
    return SYNTHETIC_TXN if a.id.startswith("syn_late") else a


def _frame(label, changed, first: BankTxn, second_amount: D, status: str) -> SplitFrame:
    total = first.amount + second_amount
    inv = Invoice(INVOICE_ID, Direction.IN, "Synthetic Buyer", first.currency, total, DUE)
    txns = [replace(first, description="part 1 %s" % INVOICE_ID)]
    if status != ABSENT:
        txns.append(BankTxn(SECOND_ID, first.currency, second_amount, D("0"), second_amount, status,
                            "part 2 %s" % INVOICE_ID, "2026-11-11T09:00:00+00:00"))
    ex, store, audit, appr = new_runtime({inv.counterparty: "ben-split"})
    r = run_cycle("SPLIT-CYCLE", AS_OF, [inv], txns, Policy({}, {}), ex, store, audit, appr)
    d, o = next((d, o) for d, o in r.outcomes if d.subject_id == INVOICE_ID)
    return SplitFrame(label, changed, first.id, status, "%.2f %s" % (total, first.currency), d.rule_id, d.action.value, o,
                      r.states[INVOICE_ID].value, d.reason)


def build_split_flow(txns: Sequence[BankTxn]) -> List[SplitFrame]:
    first = _first_part(txns)
    second = (first.amount * D("2") / D("3")).quantize(D("0.01"))
    return [
        _frame("1 part-paid", "(starting point: only the first part, as read)", first, second, ABSENT),
        _frame("2 second part sent", "second part appears as PENDING for exactly the shortfall (SIMULATED)", first, second, "PENDING"),
        _frame("3 second part in", "second part status PENDING -> SETTLED (SIMULATED)", first, second, "SETTLED"),
    ]


def render_split_flow(frames: List[SplitFrame], live: bool) -> str:
    src = ("Airwallex sandbox read: first part %s is real" % frames[0].first_id) if live and not frames[0].first_id.startswith("syn_") \
        else "no sandbox read: first part %s is SYNTHETIC" % frames[0].first_id
    out = ["== split flow: %s; invoice %s, its amount and the second part are SYNTHETIC; the second part's status is SIMULATED ==" % (src, INVOICE_ID)]
    for f in frames:
        out.append("%-18s first %s | second %s | invoice %s" % (f.label, f.first_id, f.second_status, f.invoice_amount))
        out.append("                   input changed: %s" % f.changed)
        out.append("                   -> %s / %s via %s, invoice %s: %s" % (f.action, f.outcome, f.rule, f.state, f.reason))
    return "\n".join(out) + "\n"
