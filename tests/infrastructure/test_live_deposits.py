"""Live deposits scene: several sandbox deposits of different kinds, one Closer decision each, in one log."""
import json

from closer.infrastructure.live_deposits import run_live_deposits
from tests.infrastructure.recorded_gateway import RecordedLiveGateway


def test_five_mismatch_types_each_decided_and_logged(tmp_path):
    g = RecordedLiveGateway()
    log = run_live_deposits(g, out_dir=str(tmp_path), sleep=lambda s: None)
    assert log["result"] == "OK" and len(g.deposits) == 6 and g.transfers == []
    got = {d["mismatch"]: d for d in reversed(log["decisions"])}
    assert set(got) == {"FX_DIFFERENCE", "AMOUNT_MISMATCH", "UNMATCHED_TXN", "DUPLICATE_PAYMENT"}
    assert sum(d["mismatch"] == "AMOUNT_MISMATCH" for d in log["decisions"]) == 2  # short payment + paid in another currency
    assert got["FX_DIFFERENCE"]["action"] == "AUTO_ADJUST" and got["DUPLICATE_PAYMENT"]["action"] == "HOLD_FOR_APPROVAL"
    assert got["DUPLICATE_PAYMENT"]["outcome"] == "PENDING_APPROVAL"
    assert got["AMOUNT_MISMATCH"]["action"] == got["UNMATCHED_TXN"]["action"] == "ESCALATE"
    assert all(d["evidence_txn_ids"] and d["rule_id"] for d in log["decisions"])
    assert all(d["request_id"] for d in log["deposits"])
    assert json.loads(open(log["path"]).read())["decisions"] == log["decisions"]


def test_missing_transactions_reported(tmp_path):
    g = RecordedLiveGateway()
    g.simulate_deposit = lambda *a, **k: {"id": "dep_x", "status": "PENDING"}
    log = run_live_deposits(g, out_dir=str(tmp_path), sleep=lambda s: None, attempts=2)
    assert log["result"] == "NO_TXN_APPEARED"


def test_currency_case_says_which_currency_arrived(tmp_path):
    log = run_live_deposits(RecordedLiveGateway(), out_dir=str(tmp_path), sleep=lambda s: None)
    cur = next(d for d in log["decisions"] if d["subject"].startswith("LD-CUR"))
    assert cur["action"] == "ESCALATE" and "HKD" in cur["reason"] and "USD" in cur["reason"]


def test_waits_until_new_transactions_are_settled_not_just_visible(tmp_path):
    class Slow(RecordedLiveGateway):
        reads = 0

        def list_transactions(self):
            Slow.reads += 1
            import dataclasses
            return [dataclasses.replace(t, status="PENDING") if (t.id != "old_1" and Slow.reads < 4) else t for t in self.txns]

    log = run_live_deposits(Slow(), out_dir=str(tmp_path), sleep=lambda s: None)
    assert log["result"] == "OK" and len(log["decisions"]) == 5 and all(t["status"] == "SETTLED" for t in log["transactions"])
