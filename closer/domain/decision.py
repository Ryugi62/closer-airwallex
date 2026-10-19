"""Policy -> decision. Amounts, limits and caps are enforced here, in code."""
from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional, Sequence

from .approval import ApprovalCard
from .models import Action, Finding, Invoice, Link, MismatchType as M, NON_MISMATCH
from .policy import Policy


@dataclass(frozen=True)
class Decision:
    finding: Finding
    action: Action
    rule_id: str
    amount: Decimal
    currency: str
    counterparty: str
    idempotency_key: str
    reason: str
    card: Optional[ApprovalCard] = None

    @property
    def subject_id(self) -> str:
        return self.finding.invoice_id or (self.finding.txn_ids[0] if self.finding.txn_ids else "")


def make_key(subject: str, mismatch: str, txn_ids: Sequence[str], amount: Decimal) -> str:
    raw = "|".join([subject, mismatch, ",".join(txn_ids), "%.4f" % amount])
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def decide(findings: Sequence[Finding], invoices: Sequence[Invoice], policy: Policy) -> List[Decision]:
    cp = {i.id: i.counterparty for i in invoices}
    spent: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    out: List[Decision] = []

    for f in findings:
        counterparty = cp.get(f.invoice_id or "", "UNKNOWN")
        amount = abs(f.diff)
        cur = f.currency
        card = None
        action, rule, reason = Action.NONE, "R-NONE", "no action needed"

        if f.mismatch in NON_MISMATCH:
            reason = {M.MATCHED: "invoice and settled transaction agree",
                      M.NOT_DUE: "invoice not yet due, no payment expected",
                      M.NOT_SETTLED: "transaction not settled, excluded from this cycle"}[f.mismatch]
            rule = {M.MATCHED: "R-OK-1", M.NOT_DUE: "R-OK-2", M.NOT_SETTLED: "R-OK-3"}[f.mismatch]
        elif f.mismatch == M.DUPLICATE_PAYMENT:
            action, rule = Action.HOLD_FOR_APPROVAL, "R-DUP-1"
            reason = "%d settled transactions for one invoice; surplus %.2f %s needs approval to refund" % (len(f.txn_ids), amount, cur)
            card = ApprovalCard("REFUND_SURPLUS", f.invoice_id or "", amount, cur, counterparty, tuple(f.txn_ids))
        elif f.mismatch == M.MISSING_PAYMENT:
            action, rule = Action.ESCALATE, "R-MISS-1"
            reason = "invoice past due with no settled transaction; dunning proposal for a person"
        elif f.mismatch == M.UNMATCHED_TXN:
            action, rule = Action.ESCALATE, "R-UNM-1"
            reason = "transaction matches no invoice; funds are not allocated to anyone"
        else:
            if f.mismatch == M.FEE_DEDUCTED:
                ok_rule, bad_rule, why = "R-FEE-1", "R-FEE-2", "bank fee deducted from settlement"
                eligible = amount <= policy.limit_for(cur)
            elif f.mismatch == M.FX_DIFFERENCE:
                ok_rule, bad_rule, why = "R-FX-1", "R-FX-2", "settled at a different rate than quoted (drift %.2f%%)" % (f.drift_pct or 0)
                eligible = amount <= policy.limit_for(cur) and (f.drift_pct or Decimal("0")) <= policy.fx_tolerance_pct
            else:
                ok_rule, bad_rule, why = "R-AMT-1", "R-AMT-2", "amount differs from invoice"
                eligible = amount <= policy.rounding_tolerance
                if f.paid_currency:
                    why, eligible = "payment arrived in %s but the invoice is in %s" % (f.paid_currency, cur), False
            if not eligible:
                action, rule = Action.ESCALATE, bad_rule
                reason = "%s: %.2f %s is outside the automatic limits" % (why, amount, cur)
            elif f.link == Link.INFERRED:
                action, rule = Action.ESCALATE, "R-INF-1"
                reason = "%s, but the transaction was matched by inference, not by reference" % why
            elif spent[cur] + amount > policy.cap_for(cur):
                action, rule = Action.ESCALATE, "R-CAP-1"
                reason = "%s: automatic adjustments would exceed the %s cycle cap" % (why, cur)
            else:
                action, rule = Action.AUTO_ADJUST, ok_rule
                spent[cur] += amount
                reason = "%s: %.2f %s adjusted inside limits" % (why, amount, cur)

        subject = f.invoice_id or (f.txn_ids[0] if f.txn_ids else "")
        out.append(Decision(f, action, rule, amount, cur, counterparty,
                            make_key(subject, f.mismatch.value, f.txn_ids, amount), reason, card))
    return out
