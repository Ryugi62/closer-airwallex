"""Late-payment flow: a transaction read from the sandbox is delayed, then the due date passes -> ESCALATE.
Real: transaction id, currency, amount (from the read). SYNTHETIC: the invoice and its due date.
SIMULATED: the delay (status forced to PENDING), because the sandbox does not produce late transactions on demand.
Every frame goes through the real cycle; only one input changes between frames."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal as D
from typing import List, Sequence

from closer.application.run_cycle import run_cycle
from closer.domain.models import BankTxn, Direction, Invoice
from closer.domain.policy import Policy

from .metrics import new_runtime

INVOICE_ID = "LATE-1"
DUE = date(2026, 11, 10)
BEFORE_DUE = date(2026, 11, 9)
AFTER_DUE = date(2026, 11, 12)
SYNTHETIC_TXN = BankTxn("syn_late_1", "USD", D("1250.00"), D("0"), D("1250.00"), "SETTLED",
                        "wire", "2026-11-01T09:00:00+00:00")


@dataclass(frozen=True)
class Frame:
    label: str
    changed: str
    anchor_id: str
    txn_status: str
    as_of: date
    amount: str
    mismatch_rule: str
    rule: str
    action: str
    outcome: str
    state: str
    reason: str


def pick_anchor(txns: Sequence[BankTxn]) -> BankTxn:
    for t in txns:
        if t.settled and t.amount > 0 and t.fee == 0:
            return t
    return SYNTHETIC_TXN


def _frame(label, changed, anchor: BankTxn, status: str, as_of: date) -> Frame:
    inv = Invoice(INVOICE_ID, Direction.IN, "Synthetic Buyer", anchor.currency, anchor.amount, DUE)
    txn = replace(anchor, status=status, description="wire %s" % INVOICE_ID)
    ex, store, audit, appr = new_runtime({inv.counterparty: "ben-late"})
    r = run_cycle("LATE-CYCLE", as_of, [inv], [txn], Policy({}, {}), ex, store, audit, appr)
    d, o = next((d, o) for d, o in r.outcomes if d.subject_id == INVOICE_ID)
    return Frame(label, changed, anchor.id, status, as_of, "%s %s" % (anchor.amount, anchor.currency), "",
                 d.rule_id, d.action.value, o, r.states[INVOICE_ID].value, d.reason)


def build_late_flow(txns: Sequence[BankTxn]) -> List[Frame]:
    a = pick_anchor(txns)
    return [
        _frame("1 on time", "(starting point: transaction as read)", a, "SETTLED", BEFORE_DUE),
        _frame("2 delayed", "transaction status SETTLED -> PENDING (SIMULATED delay)", a, "PENDING", BEFORE_DUE),
        _frame("3 overdue", "as-of date %s -> %s (due %s passes)" % (BEFORE_DUE, AFTER_DUE, DUE), a, "PENDING", AFTER_DUE),
    ]


def render_late_flow(frames: List[Frame], live: bool) -> str:
    src = ("Airwallex sandbox read: transaction %s is real" % frames[0].anchor_id) if live and not frames[0].anchor_id.startswith("syn_") \
        else "no sandbox read: transaction %s is SYNTHETIC" % frames[0].anchor_id
    out = ["== late flow: %s; invoice %s and its due date are SYNTHETIC; the delay is SIMULATED ==" % (src, INVOICE_ID)]
    for f in frames:
        out.append("%-11s %s | txn %s | as-of %s | %s" % (f.label, f.anchor_id, f.txn_status, f.as_of, f.amount))
        out.append("            input changed: %s" % f.changed)
        out.append("            -> %s / %s via %s, invoice %s: %s" % (f.action, f.outcome, f.rule, f.state, f.reason))
    return "\n".join(out) + "\n"
