"""Use case: one reconciliation cycle. Pure orchestration of domain rules and ports."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Sequence, Tuple

from closer.domain.approval import verify
from closer.domain.classifier import classify
from closer.domain.decision import Decision, decide
from closer.domain.models import Action, AuditEntry, BankTxn, Invoice, MismatchType as M
from closer.domain.policy import Policy
from closer.domain.state import InvoiceState as S, transition

from .ports import ApprovalSource, AuditSink, Executor, Explainer, KeyStore


@dataclass
class CycleResult:
    cycle_id: str
    decisions: List[Decision] = field(default_factory=list)
    outcomes: List[Tuple[Decision, str]] = field(default_factory=list)
    states: Dict[str, S] = field(default_factory=dict)


class _PlainExplainer:
    def explain(self, decision: Decision) -> str:
        return decision.reason


def _advance(state: S, path: Sequence[S]) -> S:
    for nxt in path:
        state = transition(state, nxt)
    return state


def run_cycle(cycle_id: str, as_of: date, invoices: Sequence[Invoice], txns: Sequence[BankTxn],
              policy: Policy, executor: Executor, store: KeyStore, audit: AuditSink,
              approvals: Optional[ApprovalSource] = None, explainer: Optional[Explainer] = None) -> CycleResult:
    explainer = explainer or _PlainExplainer()
    findings = classify(invoices, txns, as_of, policy)
    decisions = decide(findings, invoices, policy)
    result = CycleResult(cycle_id=cycle_id, decisions=decisions, states={i.id: S.OPEN for i in invoices})

    for d in decisions:
        outcome, new_state = "NO_ACTION", None
        mm = d.finding.mismatch
        if d.action == Action.NONE:
            if mm == M.NOT_SETTLED:
                outcome = "SKIPPED_NOT_SETTLED"
            elif mm == M.MATCHED:
                new_state = (S.MATCHED, S.CLOSED)
        elif store.has(d.idempotency_key):
            outcome = "SKIPPED_DUPLICATE"
            new_state = {Action.ESCALATE: (S.ESCALATED,)}.get(d.action, (S.ADJUSTED, S.CLOSED))
        elif d.action == Action.AUTO_ADJUST:
            executor.execute(d)
            store.add(d.idempotency_key)
            outcome, new_state = "EXECUTED", (S.ADJUSTED, S.CLOSED)
        elif d.action == Action.ESCALATE:
            store.add(d.idempotency_key)
            outcome, new_state = "ESCALATED", (S.ESCALATED,)
        elif d.action == Action.HOLD_FOR_APPROVAL:
            approval = approvals.find(d.finding.invoice_id or "") if approvals else None
            if approval is None:
                outcome, new_state = "PENDING_APPROVAL", (S.HELD,)
            elif not verify(d.card, approval):
                outcome, new_state = "APPROVAL_MISMATCH", (S.HELD,)
            else:
                executor.execute(d)
                store.add(d.idempotency_key)
                outcome, new_state = "EXECUTED", (S.HELD, S.ADJUSTED, S.CLOSED)

        if new_state and d.finding.invoice_id:
            result.states[d.finding.invoice_id] = _advance(S.OPEN, new_state)
        result.outcomes.append((d, outcome))
        audit.append(AuditEntry(
            cycle_id=cycle_id, subject_id=d.subject_id, mismatch=mm.value, rule_id=d.rule_id,
            evidence_txn_ids=tuple(d.finding.txn_ids), action=d.action.value, outcome=outcome,
            amount="%.2f" % d.amount, currency=d.currency, explanation=explainer.explain(d)))
    return result
