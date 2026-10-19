"""Recorded stand-in for the live gateway: deposits become settled transactions; transfers are recorded, never sent."""
from decimal import Decimal as D

from tests.helpers import txn


class RecordedLiveGateway:
    def __init__(self, existing=None):
        self.txns = list(existing or [txn(id="old_1", desc="old")])
        self.deposits, self.transfers, self.call_log = [], [], []

    def _log(self, endpoint, status, rid):
        self.call_log.append({"endpoint": endpoint, "status": status, "request_id": rid, "items": None})

    def list_global_accounts(self):
        return [{"id": "ga_1"}]

    def list_transactions(self):
        return list(self.txns)

    def simulate_deposit(self, ga, amount, currency, reference):
        n = len(self.deposits) + 1
        self.deposits.append((ga, amount, currency, reference))
        self.txns.append(txn(id="ftx_%d" % n, amount=amount, cur="HKD",  # the sandbox account settles every simulation deposit in HKD
                              desc=reference,
                             created="2026-10-20T01:00:%02d+00:00" % n))
        self._log("POST /api/v1/simulation/deposit/create", 201, "dep-r%d" % n)
        return {"id": "dep_%d" % n, "status": "PENDING"}

    def create_transfer(self, idempotency_key, beneficiary_id, amount, currency, reason):
        if any(t["request_id"] == idempotency_key for t in self.transfers):
            raise AssertionError("same request id sent twice")
        self.transfers.append({"request_id": idempotency_key, "beneficiary_id": beneficiary_id,
                               "amount": amount, "currency": currency, "reason": reason, "id": "tr_%d" % (len(self.transfers) + 1)})
        self._log("POST /api/v1/transfers/create", 201, "tr-r%d" % len(self.transfers))
        return self.transfers[-1]["id"]

    def get_transfer(self, transfer_id):
        self._log("GET /api/v1/transfers/{id}", 200, "get-r1")
        return {"id": transfer_id, "status": "PAID", "request_id": self.transfers[-1]["request_id"]}
