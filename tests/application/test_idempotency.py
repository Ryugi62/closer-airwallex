from closer.adapters.memory import InMemoryApprovals, InMemoryKeyStore, ListAuditSink, RecordingExecutor
from closer.application.run_cycle import run_cycle
from tests.helpers import AS_OF, inv, policy, txn


def test_replaying_a_cycle_20_times_executes_nothing_more():
    ex, st, au, ap = RecordingExecutor(), InMemoryKeyStore(), ListAuditSink(), InMemoryApprovals()
    invs = [inv(id="INV-1"), inv(id="INV-2")]
    txns = [txn(id="t1", fee="10", desc="INV-1"), txn(id="t2", fee="20", desc="INV-2")]
    run_cycle("C0", AS_OF, invs, txns, policy(), ex, st, au, ap)
    after_first = len(ex.calls)
    assert after_first == 2
    outcomes = []
    for i in range(20):
        r = run_cycle(f"C{i + 1}", AS_OF, invs, txns, policy(), ex, st, au, ap)
        outcomes += [o for _, o in r.outcomes]
    assert len(ex.calls) == after_first
    assert set(outcomes) == {"SKIPPED_DUPLICATE"} and len(outcomes) == 40
