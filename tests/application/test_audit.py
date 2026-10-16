from datetime import date

from closer.adapters.memory import InMemoryApprovals, InMemoryKeyStore, ListAuditSink, RecordingExecutor
from closer.application.run_cycle import run_cycle
from tests.helpers import AS_OF, inv, policy, txn


def test_every_decision_has_an_audit_entry_with_rule_and_ids():
    ex, st, au, ap = RecordingExecutor(), InMemoryKeyStore(), ListAuditSink(), InMemoryApprovals()
    invs = [inv(id="A"), inv(id="B"), inv(id="C", due=date(2026, 10, 1)), inv(id="D")]
    txns = [txn(id="t1", fee="10", desc="A"), txn(id="t2", desc="B"), txn(id="t3", amount="900", desc="D"),
            txn(id="t9", desc="mystery")]
    r = run_cycle("C1", AS_OF, invs, txns, policy(), ex, st, au, ap)
    assert len(au.entries) == len(r.decisions) > 0
    for e in au.entries:
        assert e.rule_id and (e.subject_id or e.evidence_txn_ids)
        assert e.cycle_id == "C1"


def test_not_settled_txn_is_audited():
    ex, st, au, ap = RecordingExecutor(), InMemoryKeyStore(), ListAuditSink(), InMemoryApprovals()
    run_cycle("C1", AS_OF, [], [txn(status="PENDING")], policy(), ex, st, au, ap)
    assert [e.outcome for e in au.entries] == ["SKIPPED_NOT_SETTLED"]
