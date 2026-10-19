"""Live write scene against a recorded gateway: nothing moves before the approval card is signed; one refund after; replay adds none."""
import json
from decimal import Decimal as D

from closer.infrastructure.live_write import run_live_write
from tests.infrastructure.recorded_gateway import RecordedLiveGateway

BEN = "ben_sandbox_1"


def _run(tmp_path, g=None, **kw):
    g = g or RecordedLiveGateway()
    log = run_live_write(g, beneficiary_id=BEN, beneficiary_note={"id": BEN}, out_dir=str(tmp_path), sleep=lambda s: None, **kw)
    return g, log


def test_two_deposits_one_held_card_then_exactly_one_transfer(tmp_path):
    g, log = _run(tmp_path)
    assert log["result"] == "OK"
    assert len(g.deposits) == 2 and len(g.transfers) == 1
    t = g.transfers[0]
    assert t["beneficiary_id"] == BEN and t["amount"] == D("2500.00") and t["currency"] == "HKD"
    assert log["before_approval"]["outcome"] == "PENDING_APPROVAL"
    assert log["after_approval"]["outcome"] == "EXECUTED"


def test_log_binds_card_evidence_and_request_ids(tmp_path):
    g, log = _run(tmp_path)
    card = log["approval_card"]
    assert card["amount"] == "2500.00" and card["currency"] == "HKD" and len(card["evidence_txn_ids"]) == 2
    assert log["beneficiary"] == {"id": BEN}
    assert len(card["digest"]) == 64 and log["approval"]["card_digest"] == card["digest"]
    w = log["transfer"]
    assert w["request_id"] == g.transfers[0]["request_id"] and w["id"] == "tr_1" and w["status"] == "PAID"
    assert w["http"] == 201 and w["airwallex_request_id"] == "tr-r1"
    assert [d["request_id"] for d in log["deposits"]] == ["dep-r1", "dep-r2"]
    saved = json.loads(open(log["path"]).read())
    assert saved["transfer"] == log["transfer"]


def test_replay_after_execution_sends_nothing_more(tmp_path):
    g, log = _run(tmp_path)
    assert log["replay"]["outcome"] == "SKIPPED_DUPLICATE" and len(g.transfers) == 1


def test_wrong_approval_moves_nothing(tmp_path):
    g, log = _run(tmp_path, tamper_approval=True)
    assert log["after_approval"]["outcome"] == "APPROVAL_MISMATCH"
    assert g.transfers == [] and log["transfer"] is None and log["result"] == "NOT_EXECUTED"


def test_no_settled_transactions_reports_without_writing(tmp_path):
    g = RecordedLiveGateway()
    g.simulate_deposit = lambda *a, **k: {"id": "dep_x", "status": "PENDING"}
    log = run_live_write(g, beneficiary_id=BEN, out_dir=str(tmp_path), sleep=lambda s: None, attempts=2)
    assert log["result"] == "NO_TXN_APPEARED" and g.transfers == []
