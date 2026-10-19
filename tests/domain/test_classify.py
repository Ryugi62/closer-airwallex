from datetime import date

from closer.domain.classifier import classify
from closer.domain.models import MismatchType as M
from tests.helpers import AS_OF, inv, policy, txn


def kinds(invoices, txns):
    return [(f.invoice_id, f.mismatch) for f in classify(invoices, txns, AS_OF, policy())]


def test_exact_match_is_matched():
    assert kinds([inv()], [txn()]) == [("INV-1", M.MATCHED)]


def test_fee_deducted():
    assert kinds([inv()], [txn(fee="23.50")]) == [("INV-1", M.FEE_DEDUCTED)]


def test_fx_difference_within_quoted_rate():
    i = inv(amount="1000.00", cur="EUR", settle="USD", rate="1.0800")
    t = txn(amount="1074.00", cur="USD")
    assert kinds([i], [t]) == [("INV-1", M.FX_DIFFERENCE)]


def test_duplicate_payment():
    t1, t2 = txn(id="ftx_1"), txn(id="ftx_2", created="2026-10-22T00:00:00+00:00")
    f = classify([inv()], [t1, t2], AS_OF, policy())
    assert [(x.invoice_id, x.mismatch) for x in f] == [("INV-1", M.DUPLICATE_PAYMENT)]
    assert f[0].txn_ids == ("ftx_1", "ftx_2")
    assert f[0].diff == 1000  # surplus


def test_missing_payment_when_overdue():
    assert kinds([inv(due=date(2026, 10, 1))], []) == [("INV-1", M.MISSING_PAYMENT)]


def test_not_due_is_not_a_mismatch():
    assert kinds([inv(due=date(2026, 11, 30))], []) == [("INV-1", M.NOT_DUE)]


def test_amount_mismatch_partial():
    assert kinds([inv()], [txn(amount="900.00")]) == [("INV-1", M.AMOUNT_MISMATCH)]


def test_unmatched_txn():
    f = classify([], [txn(id="ftx_9", desc="mystery wire")], AS_OF, policy())
    assert [(x.invoice_id, x.mismatch, x.txn_ids) for x in f] == [(None, M.UNMATCHED_TXN, ("ftx_9",))]


def test_not_settled_is_excluded():
    f = classify([inv(due=date(2026, 11, 30))], [txn(status="PENDING")], AS_OF, policy())
    assert {x.mismatch for x in f} == {M.NOT_DUE, M.NOT_SETTLED}


def test_inferred_link_when_no_reference_and_unique_candidate():
    f = classify([inv()], [txn(desc="wire from acme")], AS_OF, policy())
    assert f[0].mismatch == M.MATCHED and f[0].link.value == "INFERRED"


def test_six_mismatch_types_exist():
    real = {m for m in M if m not in (M.MATCHED, M.NOT_DUE, M.NOT_SETTLED)}
    assert len(real) == 6


def test_reference_linked_payment_in_other_currency_is_an_amount_mismatch_not_a_match():
    fs = classify([inv(amount="400.00", cur="USD")], [txn(amount="400.00", cur="HKD")], AS_OF, policy())
    assert [(f.invoice_id, f.mismatch, f.paid_currency) for f in fs] == [("INV-1", M.AMOUNT_MISMATCH, "HKD")]
    assert fs[0].diff == 400 and fs[0].currency == "USD"
