import pathlib
import subprocess
import sys
from decimal import Decimal as D

from closer.adapters.part_paid_flow import SYNTHETIC_TXN, build_split_flow, render_split_flow
from closer.domain.models import BankTxn

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _t(id, amount, status="SETTLED", cur="USD", fee="0"):
    a, f = D(amount), D(fee)
    return BankTxn(id, cur, a, f, a - f, status, "real description", "2026-10-12T09:00:00+00:00")


def test_three_frames_escalate_then_hold_then_close():
    frames = build_split_flow([_t("ftx_ok", "600.00")])
    assert [f.rule for f in frames] == ["R-AMT-2", "R-PART-1", "R-OK-1"]
    assert [f.action for f in frames] == ["ESCALATE", "HOLD_FOR_APPROVAL", "NONE"]
    assert [f.state for f in frames] == ["ESCALATED", "HELD", "CLOSED"]
    assert all(f.first_id == "ftx_ok" for f in frames)


def test_invoice_is_first_part_plus_second_part_and_only_second_part_changes():
    a, b, c = build_split_flow([_t("ftx_ok", "600.00")])
    assert (a.second_status, b.second_status, c.second_status) == ("(absent)", "PENDING", "SETTLED")
    assert a.invoice_amount == b.invoice_amount == c.invoice_amount
    assert a.invoice_amount == "1000.00 USD"


def test_falls_back_to_labelled_synthetic_first_part():
    frames = build_split_flow([])
    assert frames[0].first_id == SYNTHETIC_TXN.id and SYNTHETIC_TXN.id.startswith("syn_")


def test_render_labels_real_and_simulated():
    md = render_split_flow(build_split_flow([_t("ftx_ok", "600.00")]), live=True)
    assert "ftx_ok" in md and "SYNTHETIC" in md and "SIMULATED" in md and "R-PART-1" in md
    assert "no sandbox read" in render_split_flow(build_split_flow([]), live=False)


def test_cli_split_runs_offline_and_sends_nothing():
    p = subprocess.run([sys.executable, "-m", "closer", "split", "--offline"], cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert p.returncode == 0, p.stderr
    assert "R-PART-1" in p.stdout and "R-OK-1" in p.stdout and "transfers sent: 0" in p.stdout
