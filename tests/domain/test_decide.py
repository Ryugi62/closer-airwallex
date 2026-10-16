from datetime import date

from closer.domain.classifier import classify
from closer.domain.decision import decide
from closer.domain.models import Action as A
from closer.domain.models import MismatchType as M
from tests.helpers import AS_OF, D, inv, policy, txn


def run(invoices, txns, pol=None):
    pol = pol or policy()
    return decide(classify(invoices, txns, AS_OF, pol), invoices, pol)


def test_fee_within_limit_auto_adjusts():
    d = run([inv()], [txn(fee="23.50")])[0]
    assert (d.action, d.amount, d.rule_id) == (A.AUTO_ADJUST, D("23.50"), "R-FEE-1")


def test_fee_over_limit_escalates():
    d = run([inv()], [txn(fee="75.00")])[0]
    assert d.action == A.ESCALATE


def test_fx_within_tolerance_auto_adjusts():
    i = inv(cur="EUR", settle="USD", rate="1.0800")
    d = run([i], [txn(amount="1074.00", cur="USD")])[0]
    assert d.finding.mismatch == M.FX_DIFFERENCE and d.action == A.AUTO_ADJUST and d.amount == D("6.00")


def test_fx_beyond_tolerance_escalates():
    i = inv(cur="EUR", settle="USD", rate="1.0800")
    d = run([i], [txn(amount="1000.00", cur="USD")])[0]
    assert d.action == A.ESCALATE


def test_duplicate_holds_with_approval_card():
    d = run([inv()], [txn(id="a"), txn(id="b")])[0]
    assert d.action == A.HOLD_FOR_APPROVAL
    c = d.card
    assert (c.amount, c.currency, c.counterparty, c.evidence_txn_ids) == (D("1000.00"), "USD", "Acme Ltd", ("a", "b"))


def test_missing_escalates():
    assert run([inv(due=date(2026, 10, 1))], [])[0].action == A.ESCALATE


def test_rounding_amount_mismatch_auto_adjusts_but_partial_escalates():
    assert run([inv()], [txn(amount="999.70")])[0].action == A.AUTO_ADJUST
    assert run([inv()], [txn(amount="900.00")])[0].action == A.ESCALATE


def test_inferred_link_never_auto_adjusts():
    d = run([inv()], [txn(amount="1000.00", fee="10.00", desc="wire from acme")])[0]
    assert d.action == A.ESCALATE


def test_cycle_cap_forces_escalation_of_the_item_that_breaches():
    pol = policy(item_limit={"USD": D("50")}, cycle_cap={"USD": D("60")})
    invs = [inv(id="INV-1"), inv(id="INV-2")]
    txns = [txn(id="t1", fee="40", desc="INV-1"), txn(id="t2", fee="40", desc="INV-2")]
    ds = run(invs, txns, pol)
    assert [d.action for d in ds] == [A.AUTO_ADJUST, A.ESCALATE]


def test_matched_is_none():
    assert run([inv()], [txn()])[0].action == A.NONE


def test_idempotency_key_is_stable_and_distinct():
    a = run([inv()], [txn(fee="10")])[0].idempotency_key
    b = run([inv()], [txn(fee="10")])[0].idempotency_key
    c = run([inv()], [txn(fee="11")])[0].idempotency_key
    assert a == b and a != c
