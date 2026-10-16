import dataclasses

from closer.adapters.memory import InMemoryApprovals, InMemoryKeyStore, ListAuditSink, RecordingExecutor
from closer.application.run_cycle import run_cycle
from closer.domain.approval import approve
from closer.domain.models import Action as A
from closer.domain.state import InvoiceState as S
from tests.helpers import AS_OF, D, inv, policy, txn


def setup():
    return RecordingExecutor(), InMemoryKeyStore(), ListAuditSink(), InMemoryApprovals()


def cycle(invs, txns, ex, store, audit, appr, cid="C1"):
    return run_cycle(cid, AS_OF, invs, txns, policy(), ex, store, audit, appr)


def test_auto_adjust_executes_and_closes():
    ex, st, au, ap = setup()
    r = cycle([inv()], [txn(fee="23.50")], ex, st, au, ap)
    assert [o for _, o in r.outcomes] == ["EXECUTED"]
    assert len(ex.calls) == 1 and r.states["INV-1"] == S.CLOSED


def test_hold_waits_for_approval_then_executes():
    ex, st, au, ap = setup()
    invs, txns = [inv()], [txn(id="a"), txn(id="b")]
    r = cycle(invs, txns, ex, st, au, ap)
    assert [o for _, o in r.outcomes] == ["PENDING_APPROVAL"] and ex.calls == []
    assert r.states["INV-1"] == S.HELD
    card = r.decisions[0].card
    ap.put("INV-1", approve(card, "cfo"))
    r2 = cycle(invs, txns, ex, st, au, ap, cid="C2")
    assert [o for _, o in r2.outcomes] == ["EXECUTED"] and len(ex.calls) == 1


def test_stale_approval_is_rejected_and_audited():
    ex, st, au, ap = setup()
    invs, txns = [inv()], [txn(id="a"), txn(id="b")]
    r = cycle(invs, txns, ex, st, au, ap)
    stale = dataclasses.replace(r.decisions[0].card, amount=D("1.00"))
    ap.put("INV-1", approve(stale, "cfo"))
    r2 = cycle(invs, txns, ex, st, au, ap, cid="C2")
    assert [o for _, o in r2.outcomes] == ["APPROVAL_MISMATCH"] and ex.calls == []
    assert any(e.outcome == "APPROVAL_MISMATCH" for e in au.entries)


def test_escalation_is_recorded_not_executed():
    ex, st, au, ap = setup()
    r = cycle([inv()], [txn(amount="900.00")], ex, st, au, ap)
    assert [o for _, o in r.outcomes] == ["ESCALATED"] and ex.calls == [] and r.states["INV-1"] == S.ESCALATED
