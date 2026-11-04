from closer.adapters.memory import InMemoryApprovals, InMemoryKeyStore, ListAuditSink, RecordingExecutor
from closer.application.run_cycle import run_cycle
from closer.domain.classifier import classify
from closer.domain.decision import decide
from closer.domain.models import Action, MismatchType as M
from closer.domain.state import InvoiceState as S
from tests.helpers import AS_OF, inv, policy, txn

FIRST = txn("ftx_a", "600.00")


def _run(txns):
    ex, audit = RecordingExecutor(), ListAuditSink()
    r = run_cycle("C1", AS_OF, [inv()], txns, policy(), ex, InMemoryKeyStore(), audit, InMemoryApprovals())
    d, o = next((d, o) for d, o in r.outcomes if d.finding.invoice_id == "INV-1")
    return r, d, o, ex, audit


def test_shortfall_with_nothing_on_its_way_is_escalated_as_before():
    _, d, o, ex, _ = _run([FIRST])
    assert (d.finding.mismatch, d.rule_id, d.action, o) == (M.AMOUNT_MISMATCH, "R-AMT-2", Action.ESCALATE, "ESCALATED")


def test_shortfall_equal_to_referenced_in_flight_amount_is_held():
    for status in ("PENDING", "PROCESSING"):
        r, d, o, ex, audit = _run([FIRST, txn("ftx_b", "400.00", status=status)])
        assert (d.rule_id, d.action, d.card) == ("R-PART-1", Action.HOLD_FOR_APPROVAL, None)
        assert o == "PENDING_PERSON_REVIEW" and r.states["INV-1"] == S.HELD and ex.calls == []
        assert d.finding.in_flight == ("ftx_b",) and d.finding.txn_ids == ("ftx_a",)
        entry = next(e for e in audit.entries if e.subject_id == "INV-1")
        assert set(entry.evidence_txn_ids) == {"ftx_a", "ftx_b"}


def test_in_flight_that_does_not_cover_the_shortfall_exactly_does_not_hold():
    for t in (txn("ftx_b", "399.00", status="PENDING"),
              txn("ftx_b", "400.00", status="PENDING", desc="wire"),
              txn("ftx_b", "400.00", status="FAILED"),
              txn("ftx_b", "400.00", status="PENDING", cur="EUR"),
              txn("ftx_b", "-400.00", status="PENDING")):
        _, d, _, _, _ = _run([FIRST, t])
        assert d.rule_id == "R-AMT-2", t


def test_both_parts_settled_close_the_invoice():
    r, d, o, _, _ = _run([FIRST, txn("ftx_b", "400.00")])
    assert (d.finding.mismatch, d.rule_id, r.states["INV-1"]) == (M.MATCHED, "R-OK-1", S.CLOSED)


def test_two_settled_parts_over_the_invoice_stay_a_duplicate():
    f = classify([inv()], [FIRST, txn("ftx_b", "500.00")], AS_OF, policy())
    assert decide(f, [inv()], policy())[0].rule_id == "R-DUP-1"
