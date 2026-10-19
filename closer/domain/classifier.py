"""Deterministic matching and mismatch classification. No LLM, no I/O."""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Sequence

from .models import (BankTxn, Direction, Finding, Invoice, Link, MismatchType as M)
from .policy import Policy

INFER_BAND = Decimal("0.05")


def _mentions(txn: BankTxn, invoice_id: str) -> bool:
    pat = r"(?<![A-Za-z0-9-])%s(?![A-Za-z0-9-])" % re.escape(invoice_id)
    return re.search(pat, txn.description) is not None


def _direction(txn: BankTxn) -> Direction:
    return Direction.IN if txn.amount >= 0 else Direction.OUT


def _link(invoices: Sequence[Invoice], settled: Sequence[BankTxn]):
    by_inv: Dict[str, List[BankTxn]] = {i.id: [] for i in invoices}
    link_kind: Dict[str, Link] = {}
    unlinked: List[BankTxn] = []
    for t in settled:
        hit = next((i for i in invoices if _mentions(t, i.id)), None)
        if hit:
            by_inv[hit.id].append(t)
            link_kind[hit.id] = Link.REFERENCE
        else:
            unlinked.append(t)
    still: List[BankTxn] = []
    for t in unlinked:
        cands = [i for i in invoices
                 if not by_inv[i.id] and i.direction == _direction(t)
                 and i.expected_currency == t.currency
                 and i.expected_amount != 0
                 and abs(abs(t.amount) - i.expected_amount) / i.expected_amount <= INFER_BAND]
        if len(cands) == 1:
            by_inv[cands[0].id].append(t)
            link_kind[cands[0].id] = Link.INFERRED
        else:
            still.append(t)
    return by_inv, link_kind, still


def classify(invoices: Sequence[Invoice], txns: Sequence[BankTxn], as_of: date, policy: Policy) -> List[Finding]:
    findings: List[Finding] = []
    invoices = sorted(invoices, key=lambda i: i.id)
    settled = sorted([t for t in txns if t.settled], key=lambda t: (t.created_at, t.id))
    for t in sorted([t for t in txns if not t.settled], key=lambda t: t.id):
        findings.append(Finding(None, M.NOT_SETTLED, (t.id,), None, Decimal("0"), t.currency))
    by_inv, link_kind, unmatched = _link(invoices, settled)

    for inv in invoices:
        linked = by_inv[inv.id]
        cur = inv.expected_currency
        if not linked:
            kind = M.MISSING_PAYMENT if inv.due_date < as_of else M.NOT_DUE
            diff = inv.expected_amount if kind == M.MISSING_PAYMENT else Decimal("0")
            findings.append(Finding(inv.id, kind, (), None, diff, cur))
            continue
        ids = tuple(t.id for t in linked)
        link = link_kind[inv.id]
        expected = inv.expected_amount
        gross = sum((abs(t.amount) for t in linked), Decimal("0"))
        fee = sum((abs(t.fee) for t in linked), Decimal("0"))
        tol = policy.rounding_tolerance
        other = next((t.currency for t in linked if t.currency != cur), None)
        if other:  # a reference link says nothing about currency: money that arrived in another currency is not a match
            findings.append(Finding(inv.id, M.AMOUNT_MISMATCH, ids, link, expected, cur, paid_currency=other))
            continue
        if len(linked) >= 2 and gross - expected > tol:
            findings.append(Finding(inv.id, M.DUPLICATE_PAYMENT, ids, link, gross - expected, cur))
        elif inv.fx and gross != expected:
            drift = abs(gross - expected) / expected * Decimal("100")
            findings.append(Finding(inv.id, M.FX_DIFFERENCE, ids, link, expected - gross, cur, drift))
        elif gross == expected:
            kind = M.FEE_DEDUCTED if fee > 0 else M.MATCHED
            findings.append(Finding(inv.id, kind, ids, link, fee, cur))
        else:
            findings.append(Finding(inv.id, M.AMOUNT_MISMATCH, ids, link, expected - gross, cur))

    for t in unmatched:
        findings.append(Finding(None, M.UNMATCHED_TXN, (t.id,), None, abs(t.amount), t.currency))
    return findings
