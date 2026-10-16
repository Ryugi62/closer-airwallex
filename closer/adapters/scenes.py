"""Before/after scenes: change ONE input, the decision changes. Every scene is run through the real cycle.
SYNTHETIC data; ids are labelled scn_*. Input kinds: balance (cycle-cap headroom), deadline, evidence, risk."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal as D
from typing import Callable, List, Tuple

from closer.application.run_cycle import run_cycle
from closer.domain.approval import approve
from closer.domain.models import BankTxn, Direction, Invoice
from closer.domain.policy import Policy

from .metrics import new_runtime

INPUT_KINDS = ("balance", "deadline", "evidence", "risk")
LABEL = "SYNTHETIC scenes (not customer data)"


@dataclass(frozen=True)
class Outcome:
    ref: str
    txns: Tuple[str, ...]
    rule: str
    action: str
    outcome: str
    state: str


@dataclass(frozen=True)
class Scene:
    name: str
    input_kind: str
    change: str
    before: Outcome
    after: Outcome


def _inv(id, amount="1000.00", cur="USD", due=date(2026, 10, 10), settle=None, rate=None):
    return Invoice(id, Direction.IN, "Scene Buyer " + id[-1], cur, D(amount), due, settle, D(rate) if rate else None)


def _txn(id, amount, fee="0", cur="USD", desc="", status="SETTLED"):
    a, f = D(amount), D(fee)
    return BankTxn(id, cur, a, f, a - f, status, desc, "2026-10-12T09:00:00+00:00")


def _run(subject, invoices, txns, as_of=date(2026, 10, 31), limit="50", cap="100", fx="1.0", approve_it=False) -> Outcome:
    policy = Policy({"USD": D(limit), "EUR": D(limit)}, {"USD": D(cap), "EUR": D(cap)}, D(fx), D("0.50"))
    ex, store, audit, appr = new_runtime({i.counterparty: "ben-" + i.id for i in invoices})
    r = run_cycle("SCENE-1", as_of, invoices, txns, policy, ex, store, audit, appr)
    if approve_it:
        held = [d for d, o in r.outcomes if o == "PENDING_APPROVAL"]
        appr.put(held[0].card.invoice_id, approve(held[0].card, "scene-approver"))
        r = run_cycle("SCENE-2", as_of, invoices, txns, policy, ex, store, audit, appr)
    d, o = next((d, o) for d, o in r.outcomes if d.subject_id == subject)
    return Outcome(subject, tuple(d.finding.txn_ids), d.rule_id, d.action.value, o,
                   r.states.get(subject, None).value if subject in r.states else "OPEN")


def build_scenes() -> List[Scene]:
    s: List[Scene] = []
    two_fees = [_inv("INV-901"), _inv("INV-902")]
    two_txns = [_txn("scn_0001", "1000.00", "30.00", desc="wire INV-901"), _txn("scn_0002", "1000.00", "30.00", desc="wire INV-902")]
    s.append(Scene("balance: cycle cap headroom", "balance", "per-currency adjustment cap 100 -> 50 (second 30.00 fee no longer fits)",
                   _run("INV-902", two_fees, two_txns, cap="100"), _run("INV-902", two_fees, two_txns, cap="50")))
    unpaid = [_inv("INV-911", due=date(2026, 10, 20))]
    s.append(Scene("deadline: due date passes", "deadline", "as-of date 2026-10-15 -> 2026-10-31 (invoice due 2026-10-20, no payment)",
                   _run("INV-911", unpaid, [], as_of=date(2026, 10, 15)), _run("INV-911", unpaid, [], as_of=date(2026, 10, 31))))
    inv = [_inv("INV-921", "500.00")]
    ref = [_txn("scn_0003", "500.00", "20.00", desc="wire INV-921")]
    noref = [_txn("scn_0003", "500.00", "20.00", desc="wire from buyer")]
    s.append(Scene("evidence: reference present or not", "evidence", "transaction description loses the invoice id (link falls back to inference)",
                   _run("INV-921", inv, ref), _run("INV-921", inv, noref)))
    fx = [_inv("INV-931", "1000.00", "EUR", settle="USD", rate="1.0800")]
    small = [_txn("scn_0004", "1074.00", desc="FX settlement INV-931")]
    big = [_txn("scn_0004", "1050.00", desc="FX settlement INV-931")]
    s.append(Scene("risk: FX drift grows", "risk", "settled USD 1074.00 -> 1050.00 against the quoted 1080.00 (drift 0.56% -> 2.78%, tolerance 1.0%)",
                   _run("INV-931", fx, small), _run("INV-931", fx, big)))
    dup = [_inv("INV-941", "2500.00")]
    dups = [_txn("scn_0005", "2500.00", desc="payment INV-941"), _txn("scn_0006", "2500.00", desc="payment INV-941 resent")]
    s.append(Scene("approval: a person signs the card", "approval", "approval card for the surplus 2500.00 USD is approved (before: not yet)",
                   _run("INV-941", dup, dups), _run("INV-941", dup, dups, approve_it=True)))
    return s


def render_markdown(scenes: List[Scene]) -> str:
    rows = ["%s" % LABEL, "", "| Scene | Input that changes | Before: decision (rule, evidence) | After: decision (rule, evidence) | Ends as |",
            "|---|---|---|---|---|"]
    for sc in scenes:
        f = lambda o: "%s / %s (%s; %s)" % (o.action, o.outcome, o.rule, ", ".join(o.txns) or "no txn")
        rows.append("| %s | %s | %s | %s | %s %s |" % (sc.name, sc.change, f(sc.before), f(sc.after), sc.after.ref, sc.after.state))
    return "\n".join(rows) + "\n"
