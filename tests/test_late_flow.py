import pathlib
import subprocess
import sys
from decimal import Decimal as D

from closer.adapters.late_flow import SYNTHETIC_TXN, build_late_flow, pick_anchor, render_late_flow
from closer.domain.models import BankTxn

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _t(id, amount, fee="0", status="SETTLED", cur="USD"):
    a, f = D(amount), D(fee)
    return BankTxn(id, cur, a, f, a - f, status, "real description", "2026-10-12T09:00:00+00:00")


def test_pick_anchor_takes_first_settled_inbound_without_fee():
    txns = [_t("ftx_out", "-5"), _t("ftx_pend", "7", status="PENDING"), _t("ftx_fee", "9", fee="1"), _t("ftx_ok", "10")]
    assert pick_anchor(txns).id == "ftx_ok"


def test_pick_anchor_falls_back_to_labelled_synthetic():
    assert pick_anchor([_t("ftx_out", "-5")]) is SYNTHETIC_TXN and SYNTHETIC_TXN.id.startswith("syn_")


def test_four_frames_hold_while_payment_is_in_transit_and_escalate_only_when_nothing_is_coming():
    frames = build_late_flow([_t("ftx_ok", "1250.00")])
    assert [f.action for f in frames] == ["NONE", "NONE", "HOLD_FOR_APPROVAL", "ESCALATE"]
    assert [f.rule for f in frames] == ["R-OK-1", "R-OK-2", "R-LATE-1", "R-MISS-1"]
    assert frames[0].state == "CLOSED" and frames[2].state == "HELD" and frames[3].state == "ESCALATED"
    assert frames[2].outcome == "PENDING_PERSON_REVIEW" and frames[3].outcome == "ESCALATED"
    assert all(f.anchor_id == "ftx_ok" for f in frames)


def test_only_the_stated_input_changes_between_frames():
    a, b, c, d = build_late_flow([_t("ftx_ok", "1250.00")])
    assert (a.txn_status, b.txn_status, c.txn_status) == ("SETTLED", "PENDING", "PENDING")
    assert a.as_of == b.as_of and b.as_of < c.as_of == d.as_of
    assert c.amount == "1250.00 USD"


def test_render_labels_what_is_real_and_what_is_simulated():
    md = render_late_flow(build_late_flow([_t("ftx_ok", "1250.00")]), live=True)
    assert "ftx_ok" in md and "SYNTHETIC" in md and "SIMULATED" in md and "ESCALATE" in md
    assert "Airwallex sandbox" in md
    off = render_late_flow(build_late_flow([]), live=False)
    assert "syn_" in off and "no sandbox read" in off


def test_cli_late_runs_offline_and_ends_escalated():
    p = subprocess.run([sys.executable, "-m", "closer", "late", "--offline"], cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert p.returncode == 0, p.stderr
    assert "R-LATE-1" in p.stdout and "ESCALATE" in p.stdout and "R-MISS-1" in p.stdout and "transfers sent: 0" in p.stdout
