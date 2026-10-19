"""Live-deposit scene: one sandbox simulation deposit is created, read back, and decided by one Closer cycle.
Ledger is SYNTHETIC (one invoice billed above the deposit); the transaction is real sandbox data. No transfer is written."""
from __future__ import annotations

import json
import os
import time
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Dict, Optional

from closer.adapters.memory import ListAuditSink
from closer.application.run_cycle import run_cycle
from closer.domain.models import Direction, Invoice
from closer.domain.policy import Policy

from closer.adapters.metrics import new_runtime

SHORTFALL = Decimal("12.00")


def run_live_deposit(gw: Any, currency: str = "HKD", amount: Decimal = Decimal("1000.00"), out_dir: str = "out",
                     sleep: Callable[[float], None] = time.sleep, attempts: int = 8) -> Dict[str, Any]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ref = "LIVE-DEP-" + stamp
    before = {t.id for t in gw.list_transactions()}
    accounts = gw.list_global_accounts()
    log: Dict[str, Any] = {"generated_at": stamp, "label": "sandbox simulation deposit; ledger SYNTHETIC; no transfer written",
                           "global_account_id": accounts[0]["id"] if accounts else None, "reference": ref,
                           "deposit": None, "transaction": None, "decision": None, "result": None}
    resp = gw.simulate_deposit(log["global_account_id"], str(amount), currency, ref)
    log["deposit"] = {"id": resp.get("id"), "status": resp.get("status"), "request_id": gw.call_log[-1]["request_id"],
                      "http": gw.call_log[-1]["status"]}
    new = []
    for _ in range(attempts):
        new = [t for t in gw.list_transactions() if t.id not in before]
        if new:
            break
        sleep(2)
    if not new:
        log["result"] = "NO_TXN_APPEARED"
    else:
        t = new[0]
        log["transaction"] = {"id": t.id, "currency": t.currency, "amount": str(t.amount), "fee": str(t.fee),
                              "status": t.status, "description": t.description, "created_at": t.created_at}
        inv = Invoice(id=ref, direction=Direction.IN, counterparty="Sandbox Customer (synthetic ledger)",
                      currency=t.currency, amount=abs(t.amount) + SHORTFALL, due_date=date.today())
        ex, store, _, appr = new_runtime({})
        audit = ListAuditSink()
        r = run_cycle("LIVE-DEP-" + stamp, date.today(), [inv], new, Policy(item_limit={}, cycle_cap={}), ex, store, audit, appr)
        d, outcome = next((d, o) for d, o in r.outcomes if d.action.value != "NONE")
        log["decision"] = {"subject": d.subject_id, "mismatch": d.finding.mismatch.value, "rule_id": d.rule_id,
                           "action": d.action.value, "outcome": outcome, "evidence_txn_ids": list(d.finding.txn_ids),
                           "reason": d.reason}
        log["result"] = "OK"
    log["calls"] = gw.call_log
    os.makedirs(out_dir, exist_ok=True)
    log["path"] = os.path.join(out_dir, "live-deposit-%s.json" % stamp)
    with open(log["path"], "w") as fh:
        json.dump(log, fh, indent=2)
    return log
