"""Live-deposits scene (sandbox / demo environment): several simulation deposits of different kinds are created, read
back, and decided by one Closer cycle. Ledger is SYNTHETIC; transactions are real sandbox data. No transfer is written."""
from __future__ import annotations

import time
from datetime import date, datetime, timezone
from decimal import Decimal as D
from typing import Any, Callable, Dict, List

from closer.adapters.metrics import new_runtime
from closer.application.run_cycle import run_cycle
from closer.domain.models import Direction, Invoice
from closer.domain.policy import Policy

from .live_common import save, wait_for_new

PAYER = "Closer Sandbox Customer"


def run_live_deposits(gw: Any, out_dir: str, sleep: Callable[[float], None] = time.sleep, attempts: int = 20) -> Dict[str, Any]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    r = lambda kind: "LD-%s-%s" % (kind, stamp)  # noqa: E731
    # (reference, currency, deposit amounts, invoice) : each row is meant to land on a different mismatch type
    H = "HKD"
    plan = [
        ("fx", H, ["8350.00"], Invoice(id=r("FX"), direction=Direction.IN, counterparty=PAYER, currency="EUR", amount=D("1000.00"),
                                       due_date=date.today(), settlement_currency=H, quoted_rate=D("8.4000"))),
        ("amt", H, ["388.00"], Invoice(id=r("AMT"), direction=Direction.IN, counterparty=PAYER, currency=H, amount=D("400.00"), due_date=date.today())),
        ("dup", H, ["750.00", "750.00"], Invoice(id=r("DUP"), direction=Direction.IN, counterparty=PAYER, currency=H, amount=D("750.00"), due_date=date.today())),
        ("unk", H, ["321.00"], None),
        # asked in USD; the sandbox account settles every simulation deposit in HKD (observed 2026-10-19), so the invoice in USD is not paid in USD
        ("cur", "USD", ["400.00"], Invoice(id=r("CUR"), direction=Direction.IN, counterparty=PAYER, currency="USD", amount=D("400.00"), due_date=date.today())),
    ]
    before = {t.id for t in gw.list_transactions()}
    account = gw.list_global_accounts()[0]["id"]
    log: Dict[str, Any] = {"generated_at": stamp, "label": "sandbox (demo environment) simulation deposits; ledger SYNTHETIC; no transfer written",
                           "deposits": [], "transactions": [], "decisions": [], "result": None}
    for kind, cur, amounts, invoice in plan:
        ref = invoice.id if invoice else "UNKNOWN-REF-" + stamp
        for a in amounts:
            resp = gw.simulate_deposit(account, a, cur, ref)
            c = gw.call_log[-1] if gw.call_log else {"request_id": None, "status": None}
            log["deposits"].append({"kind": kind, "reference": ref, "amount": a, "currency": cur, "id": resp.get("id"),
                                    "status": resp.get("status"), "request_id": c["request_id"], "http": c["status"]})
    new = wait_for_new(gw, before, len(log["deposits"]), sleep, attempts)
    if len(new) < len(log["deposits"]) or not all(t.settled for t in new):
        log["result"] = "NO_TXN_APPEARED"
        log["calls"] = gw.call_log
        save(log, out_dir, "live-deposits-%s.json" % stamp)
        return log
    log["transactions"] = [{"id": t.id, "currency": t.currency, "amount": str(t.amount), "fee": str(t.fee), "status": t.status,
                            "description": t.description} for t in new]
    invoices: List[Invoice] = [p[3] for p in plan if p[3]]
    policy = Policy(item_limit={"HKD": D("100")}, cycle_cap={"HKD": D("500")})
    ex, store, audit, appr = new_runtime({})
    res = run_cycle("LD-" + stamp, date.today(), invoices, new, policy, ex, store, audit, appr)
    for d, outcome in res.outcomes:
        if d.action.value == "NONE":
            continue
        log["decisions"].append({"subject": d.subject_id, "mismatch": d.finding.mismatch.value, "rule_id": d.rule_id,
                                 "action": d.action.value, "outcome": outcome, "evidence_txn_ids": list(d.finding.txn_ids),
                                 "amount": "%.2f" % d.amount, "currency": d.currency, "reason": d.reason})
    log["result"] = "OK"
    log["calls"] = gw.call_log
    save(log, out_dir, "live-deposits-%s.json" % stamp)
    return log
