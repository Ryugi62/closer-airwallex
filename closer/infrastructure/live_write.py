"""Live-write scene (sandbox / demo environment only): a duplicate payment is created with two simulation deposits,
held behind one approval card, and after approval exactly one refund transfer is written. Ledger is SYNTHETIC; the
beneficiary is a pre-existing sandbox beneficiary, not the simulated payer. Production writes are out of scope."""
from __future__ import annotations

import time
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

from closer.adapters.executors import RoutingExecutor
from closer.adapters.memory import InMemoryApprovals, InMemoryKeyStore, ListAuditSink
from closer.application.run_cycle import run_cycle
from closer.domain.approval import ApprovalCard, approve
from closer.domain.models import Direction, Invoice
from closer.domain.policy import Policy

from .live_common import last_call, save, wait_for_new

PAYER = "Closer Sandbox Customer"
CREATE = "POST /api/v1/transfers/create"


class _Recording(RoutingExecutor):
    def __init__(self, gw: Any, beneficiaries: Dict[str, str]) -> None:
        super().__init__(gw, beneficiaries)
        self.results: List[str] = []

    def execute(self, decision: Any) -> str:
        out = super().execute(decision)
        self.results.append(out)
        return out


def _step(r: Any) -> Dict[str, Any]:
    d, outcome = next((d, o) for d, o in r.outcomes if d.action.value != "NONE")
    return {"mismatch": d.finding.mismatch.value, "rule_id": d.rule_id, "action": d.action.value, "outcome": outcome}


def run_live_write(gw: Any, beneficiary_id: str, out_dir: str, currency: str = "HKD", amount: Decimal = Decimal("2500.00"),
                   approver: str = "operator-command", beneficiary_note: Optional[Dict[str, Any]] = None, tamper_approval: bool = False,
                   sleep: Callable[[float], None] = time.sleep, attempts: int = 20) -> Dict[str, Any]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ref = "INV-LW-" + stamp
    before = {t.id for t in gw.list_transactions()}
    account = gw.list_global_accounts()[0]["id"]
    log: Dict[str, Any] = {"generated_at": stamp, "label": "sandbox (demo environment) write; ledger SYNTHETIC; beneficiary is a pre-existing sandbox beneficiary",
                           "invoice": ref, "beneficiary": beneficiary_note, "deposits": [], "transactions": [], "approval_card": None, "approval": None,
                           "before_approval": None, "after_approval": None, "replay": None, "transfer": None, "result": None}
    for _ in range(2):
        resp = gw.simulate_deposit(account, str(amount), currency, ref)
        c = gw.call_log[-1] if gw.call_log else {"request_id": None, "status": None}
        log["deposits"].append({"id": resp.get("id"), "status": resp.get("status"), "request_id": c["request_id"], "http": c["status"]})
    new = wait_for_new(gw, before, 2, sleep, attempts)
    if len(new) < 2 or not all(t.settled for t in new):
        log["result"] = "NO_TXN_APPEARED"
        log["calls"] = gw.call_log
        save(log, out_dir, "live-write-%s.json" % stamp)
        return log
    log["transactions"] = [{"id": t.id, "currency": t.currency, "amount": str(t.amount), "status": t.status} for t in new]
    inv = Invoice(id=ref, direction=Direction.IN, counterparty=PAYER, currency=currency, amount=amount, due_date=date.today())
    policy = Policy(item_limit={}, cycle_cap={})
    ex, store, audit, appr = _Recording(gw, {PAYER: beneficiary_id}), InMemoryKeyStore(), ListAuditSink(), InMemoryApprovals()

    r1 = run_cycle("LW1-" + stamp, date.today(), [inv], new, policy, ex, store, audit, appr)
    log["before_approval"] = _step(r1)
    card = next(d.card for d, _ in r1.outcomes if d.card)
    log["approval_card"] = {"action": card.action, "invoice_id": card.invoice_id, "amount": "%.2f" % card.amount, "currency": card.currency,
                            "counterparty": card.counterparty, "evidence_txn_ids": list(card.evidence_txn_ids), "digest": card.digest()}
    signed = card
    if tamper_approval:
        signed = ApprovalCard(card.action, card.invoice_id, card.amount + Decimal("1"), card.currency, card.counterparty, card.evidence_txn_ids)
    approval = approve(signed, approver)
    log["approval"] = {"approver": approver, "card_digest": approval.card_digest}
    appr.put(inv.id, approval)

    r2 = run_cycle("LW2-" + stamp, date.today(), [inv], new, policy, ex, store, audit, appr)
    log["after_approval"] = _step(r2)
    if ex.results:
        c = last_call(gw, CREATE)
        tid = ex.results[0]
        got = gw.get_transfer(tid)
        log["transfer"] = {"id": tid, "status": got.get("status"), "request_id": next(d.idempotency_key for d, _ in r2.outcomes if d.card),
                           "http": c["status"], "airwallex_request_id": c["request_id"], "amount": "%.2f" % card.amount, "currency": currency}
        r3 = run_cycle("LW3-" + stamp, date.today(), [inv], new, policy, ex, store, audit, appr)
        log["replay"] = _step(r3)
        log["result"] = "OK" if len(ex.results) == 1 else "REPLAY_EXECUTED_AGAIN"
    else:
        log["result"] = "NOT_EXECUTED"
    log["audit_entries"] = len(audit.entries)
    log["calls"] = gw.call_log
    save(log, out_dir, "live-write-%s.json" % stamp)
    return log
