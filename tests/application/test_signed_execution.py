import dataclasses

from closer.adapters.memory import InMemoryApprovals, InMemoryKeyStore, ListAuditSink, RecordingExecutor
from closer.application.run_cycle import run_cycle
from closer.domain.signing import ApproverAuthority, Signer
from tests.helpers import AS_OF, inv, policy, txn

APPROVER_KEY = b"A" * 32
EXECUTOR_KEY = b"E" * 32


def _held():
    ex, st, au, ap = RecordingExecutor(), InMemoryKeyStore(), ListAuditSink(), InMemoryApprovals()
    invs = [inv(id="INV-1")]
    txns = [txn(id="a", desc="INV-1"), txn(id="b", desc="INV-1")]
    r = run_cycle("C1", AS_OF, invs, txns, policy(), ex, st, au, ap)
    card = next(d.card for d, o in r.outcomes if o == "PENDING_APPROVAL")
    return ex, st, au, ap, invs, txns, card


def _second(ex, st, au, ap, invs, txns, verifier):
    r = run_cycle("C2", AS_OF, invs, txns, policy(), ex, st, au, ap, verifier=verifier)
    return [o for d, o in r.outcomes if d.card]


def test_approver_signed_card_executes_once():
    ex, st, au, ap, invs, txns, card = _held()
    auth = ApproverAuthority(APPROVER_KEY)
    ap.put("INV-1", auth.sign(card, "cfo"))
    assert _second(ex, st, au, ap, invs, txns, auth.verify) == ["EXECUTED"]
    assert len(ex.calls) == 1


def test_executor_signed_card_is_rejected_and_not_executed():
    ex, st, au, ap, invs, txns, card = _held()
    auth = ApproverAuthority(APPROVER_KEY)
    ap.put("INV-1", Signer("executor", EXECUTOR_KEY).sign(card, "executor-bot"))
    assert _second(ex, st, au, ap, invs, txns, auth.verify) == ["APPROVAL_SIGNATURE_INVALID"]
    assert ex.calls == []


def test_digest_changed_by_one_byte_is_rejected_and_not_executed():
    ex, st, au, ap, invs, txns, card = _held()
    auth = ApproverAuthority(APPROVER_KEY)
    good = auth.sign(card, "cfo")
    d = good.card_digest
    ap.put("INV-1", dataclasses.replace(good, card_digest=d[:-1] + ("0" if d[-1] != "0" else "1")))
    assert _second(ex, st, au, ap, invs, txns, auth.verify) == ["APPROVAL_SIGNATURE_INVALID"]
    assert ex.calls == []
