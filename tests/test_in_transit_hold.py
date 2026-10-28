from closer.adapters.memory import InMemoryApprovals, InMemoryKeyStore, ListAuditSink, RecordingExecutor
from closer.application.run_cycle import run_cycle
from closer.domain.classifier import classify
from closer.domain.decision import decide
from closer.domain.models import Action, MismatchType as M
from closer.domain.state import InvoiceState as S
from tests.helpers import AS_OF, inv, policy, txn


def _run(txns):
    ex = RecordingExecutor()
    r = run_cycle("C1", AS_OF, [inv()], txns, policy(), ex, InMemoryKeyStore(), ListAuditSink(), InMemoryApprovals())
    return r, ex


def test_overdue_invoice_with_referenced_pending_payment_is_held_not_dunned():
    for status in ("PENDING", "PROCESSING"):
        r, ex = _run([txn(status=status)])
        d, o = r.outcomes[0] if r.outcomes[0][0].finding.invoice_id else r.outcomes[1]
        assert (d.action, d.rule_id, d.card) == (Action.HOLD_FOR_APPROVAL, "R-LATE-1", None)
        assert o == "PENDING_PERSON_REVIEW" and r.states["INV-1"] == S.HELD and ex.calls == []
        assert d.finding.txn_ids == ("ftx_1",)


def test_overdue_invoice_with_no_transaction_is_still_escalated():
    f = classify([inv()], [], AS_OF, policy())
    d = decide(f, [inv()], policy())[0]
    assert (f[0].mismatch, d.action, d.rule_id) == (M.MISSING_PAYMENT, Action.ESCALATE, "R-MISS-1")


def test_pending_payment_without_the_invoice_reference_does_not_hold():
    d = [x for x in decide(classify([inv()], [txn(status="PENDING", desc="wire")], AS_OF, policy()), [inv()], policy())
         if x.finding.invoice_id == "INV-1"][0]
    assert d.rule_id == "R-MISS-1"


def test_failed_payment_does_not_hold():
    d = [x for x in decide(classify([inv()], [txn(status="FAILED")], AS_OF, policy()), [inv()], policy())
         if x.finding.invoice_id == "INV-1"][0]
    assert d.rule_id == "R-MISS-1"
