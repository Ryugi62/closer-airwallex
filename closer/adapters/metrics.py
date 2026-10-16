"""Metrics over a scenario: closer vs the exact-match baseline a spreadsheet would give."""
from __future__ import annotations

import re
from collections import Counter
from typing import Dict, List, Tuple

from closer.application.roi import roi_krw
from closer.application.run_cycle import run_cycle
from closer.domain.models import NON_MISMATCH

from .executors import FakeTransferGateway, RoutingExecutor
from .memory import InMemoryApprovals, InMemoryKeyStore, ListAuditSink


def baseline_exceptions(invoices, txns, as_of) -> int:
    settled = [t for t in txns if t.settled]
    exc, used = 0, set()
    for i in invoices:
        pat = r"(?<![A-Za-z0-9-])%s(?![A-Za-z0-9-])" % re.escape(i.id)
        hits = [t for t in settled if re.search(pat, t.description)]
        used.update(t.id for t in hits)
        clean = len(hits) == 1 and hits[0].amount == i.amount and hits[0].currency == i.currency and hits[0].fee == 0
        if not hits and i.due_date >= as_of:
            continue
        if not clean:
            exc += 1
    exc += sum(1 for t in settled if t.id not in used)
    return exc


def new_runtime(beneficiaries=None):
    ben = beneficiaries or {}
    return RoutingExecutor(FakeTransferGateway(), ben), InMemoryKeyStore(), ListAuditSink(), InMemoryApprovals()


def compute_metrics(invoices, txns, as_of, policy) -> Tuple[Dict, List[Dict]]:
    ex, store, audit, appr = new_runtime({i.counterparty: "ben-" + i.id for i in invoices})
    r = run_cycle("M0", as_of, invoices, txns, policy, ex, store, audit, appr)
    first_exec = len(ex.journal) + len(ex.gateway.sent)
    for k in range(20):
        run_cycle("M%d" % (k + 1), as_of, invoices, txns, policy, ex, store, audit, appr)
    extra = len(ex.journal) + len(ex.gateway.sent) - first_exec
    report = [{"subject": d.subject_id, "mismatch": d.finding.mismatch.value, "rule": d.rule_id, "action": d.action.value,
               "outcome": o, "amount": "%.2f" % d.amount, "currency": d.currency, "evidence": list(d.finding.txn_ids),
               "reason": d.reason} for d, o in r.outcomes]
    out = Counter(x["outcome"] for x in report)
    types = {x["mismatch"] for x in report if x["mismatch"] not in {m.value for m in NON_MISMATCH}}
    m = {
        "invoices": len(invoices), "transactions": len(txns),
        "baseline_exceptions": baseline_exceptions(invoices, txns, as_of),
        "auto_adjusted": out["EXECUTED"], "held": out["PENDING_APPROVAL"], "escalated": out["ESCALATED"],
        "matched_clean": sum(1 for x in report if x["mismatch"] == "MATCHED"),
        "mismatch_types_seen": len(types),
        "replay_runs": 20, "replay_extra_executions": extra,
        "audit_entries": len(audit.entries) // 21, "decisions": len(r.decisions),
    }
    m["closer_human_items"] = m["held"] + m["escalated"]
    m.update({"roi_" + k: v for k, v in roi_krw(m["baseline_exceptions"], m["closer_human_items"]).items()})
    return m, report
