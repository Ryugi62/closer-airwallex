"""The live-deposit scene against a recorded gateway: one simulated deposit becomes one decision with ids in the log."""
import json
from decimal import Decimal as D

from closer.infrastructure.live_deposit import run_live_deposit
from tests.helpers import txn


class RecordedGateway:
    def __init__(self, seen_after):
        self.before, self.after = [txn(id="old_1", desc="old")], seen_after
        self.calls, self.call_log, self._n = [], [], 0

    def list_global_accounts(self):
        return [{"id": "ga_1", "status": "ACTIVE"}]

    def list_transactions(self):
        self._n += 1
        return self.before if not self.calls else self.after

    def simulate_deposit(self, ga, amount, currency, reference):
        self.calls.append((ga, amount, currency, reference))
        self.call_log.append({"endpoint": "POST /api/v1/simulation/deposit/create", "status": 201, "request_id": "sim-r1", "items": None})
        return {"id": "dep_1", "status": "PENDING"}


def test_live_deposit_logs_request_id_txn_id_and_one_decision(tmp_path):
    new = txn(id="ftx_new", amount="1000.00", desc="LIVE-DEP-1 deposit", created="2026-10-20T01:00:00+00:00")
    g = RecordedGateway([txn(id="old_1", desc="old"), new])
    log = run_live_deposit(g, currency="USD", amount=D("1000.00"), out_dir=str(tmp_path), sleep=lambda s: None)
    assert log["result"] == "OK" and log["deposit"]["request_id"] == "sim-r1" and log["deposit"]["id"] == "dep_1"
    assert log["transaction"]["id"] == "ftx_new"
    assert log["decision"]["mismatch"] == "AMOUNT_MISMATCH" and log["decision"]["action"] == "ESCALATE"
    assert log["decision"]["evidence_txn_ids"] == ["ftx_new"]
    saved = json.loads(open(log["path"]).read())
    assert saved["decision"] == log["decision"]


def test_live_deposit_reports_when_no_transaction_appears(tmp_path):
    g = RecordedGateway([txn(id="old_1", desc="old")])
    log = run_live_deposit(g, currency="USD", amount=D("1000.00"), out_dir=str(tmp_path), sleep=lambda s: None, attempts=2)
    assert log["result"] == "NO_TXN_APPEARED" and log["decision"] is None and log["deposit"]["id"] == "dep_1"
