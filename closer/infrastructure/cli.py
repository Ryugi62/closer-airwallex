"""Composition root + CLI. `python3 -m closer <demo|metrics|scenes|card|reconcile|live-smoke|live-cycle|readme>`."""
from __future__ import annotations

import json
import os
import sys
import argparse
from datetime import date, datetime, timezone
from decimal import Decimal

from closer.adapters.airwallex_http import AirwallexGateway
from closer.adapters.csv_ledger import InputError, load_ledger, load_txns
from closer.adapters.memory import InMemoryApprovals, InMemoryKeyStore, JsonlAuditSink, ListAuditSink
from closer.adapters.metrics import compute_metrics, new_runtime
from closer.adapters.scenario import LABEL, scenario_pack
from closer.application.run_cycle import run_cycle
from closer.domain.approval import approve
from closer.domain.policy import Policy

from .http_transport import urllib_transport
from .keychain import credentials

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS = os.path.join(ROOT, "docs")


def _print_table(r):
    print("%-10s %-18s %-9s %-18s %-17s %10s" % ("subject", "mismatch", "rule", "action", "outcome", "amount"))
    for d, o in r.outcomes:
        if d.action.value != "NONE":
            print("%-10s %-18s %-9s %-18s %-17s %10s %s" % (d.subject_id, d.finding.mismatch.value, d.rule_id, d.action.value, o,
                                                           "%.2f" % d.amount, d.currency))


def cmd_demo() -> int:
    invoices, txns, as_of, policy = scenario_pack()
    ben = {i.counterparty: "ben-" + i.id for i in invoices}
    ex, store, _, appr = new_runtime(ben)
    audit = JsonlAuditSink(os.path.join(ROOT, "out", "audit.jsonl"))
    print("== Closer demo ==  " + LABEL + " ; refunds go to a FAKE transfer gateway (no network)")
    r = run_cycle("DEMO-1", as_of, invoices, txns, policy, ex, store, audit, appr)
    print("\n-- cycle 1: decisions (no LLM involved) --")
    _print_table(r)
    held = [d for d, o in r.outcomes if o == "PENDING_APPROVAL"]
    card = held[0].card
    print("\n-- approval card (bound to amount, currency, counterparty, evidence) --")
    print("  invoice=%s amount=%.2f %s counterparty=%s evidence=%s" % (card.invoice_id, card.amount, card.currency, card.counterparty, list(card.evidence_txn_ids)))
    appr.put(card.invoice_id, approve(card, "demo-approver"))
    r2 = run_cycle("DEMO-2", as_of, invoices, txns, policy, ex, store, audit, appr)
    print("\n-- cycle 2 after approving %s --" % card.invoice_id)
    for d, o in r2.outcomes:
        if d.subject_id == card.invoice_id:
            print("  %s -> %s (refund request_id=%s... sent via FAKE gateway: %s)" % (d.subject_id, o, d.idempotency_key[:10], ex.gateway.sent[-1]["id"] if ex.gateway.sent else "-"))
    skipped = sum(1 for _, o in r2.outcomes if o == "SKIPPED_DUPLICATE")
    print("  %d decisions from cycle 1 were skipped as duplicates (executed once, never twice)" % skipped)
    print("\naudit log: out/audit.jsonl (%d entries)" % len(audit.entries))
    return 0


def cmd_metrics() -> int:
    m, _ = compute_metrics(*scenario_pack())
    print(json.dumps(m, indent=2, sort_keys=True))
    return 0


def _gateway():
    cred = credentials()
    if not cred:
        return None
    return AirwallexGateway(urllib_transport, client_id=cred[0], api_key=cred[1])


def cmd_live_smoke() -> int:
    gw = _gateway()
    if gw is None:
        print("no sandbox credentials (env AIRWALLEX_CLIENT_ID/AIRWALLEX_API_KEY or keychain); live-smoke skipped")
        return 3
    gw.list_balances(); gw.list_transactions(); gw.list_transfers(); gw.list_global_accounts()
    gw.list_beneficiaries(); gw.list_deposits(); gw.list_fx_conversions(); gw.balances_history()
    log = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "base": "https://api-demo.airwallex.com",
           "calls": gw.call_log}
    os.makedirs(DOCS, exist_ok=True)
    with open(os.path.join(DOCS, "endpoint-log.json"), "w") as fh:
        json.dump(log, fh, indent=2)
    for c in gw.call_log:
        print("%-45s HTTP %s  request_id=%s  items=%s" % (c["endpoint"], c["status"], c["request_id"], c["items"]))
    print("distinct endpoints:", len({c["endpoint"] for c in gw.call_log}))
    return 0


def cmd_live_cycle() -> int:
    gw = _gateway()
    if gw is None:
        print("no sandbox credentials; live-cycle skipped")
        return 3
    txns = gw.list_transactions()
    invoices = load_ledger(os.path.join(ROOT, "data", "live_ledger.csv"))
    policy = Policy(item_limit={}, cycle_cap={})
    ex, store, audit, appr = new_runtime({})
    print("== live-cycle: TRANSACTIONS = Airwallex sandbox (%d read) ; LEDGER = SYNTHETIC data/live_ledger.csv ==" % len(txns))
    r = run_cycle("LIVE-%s" % date.today().isoformat(), date.today(), invoices, txns, policy, ex, store, audit, appr)
    _print_table(r)
    return 0


def cmd_reconcile(argv) -> int:
    """Run one cycle on the caller's own ledger and transactions (CSV). Refunds go to a fake gateway."""
    ap = argparse.ArgumentParser(prog="closer reconcile")
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--txns", required=True)
    ap.add_argument("--as-of", default=date.today().isoformat())
    ap.add_argument("--item-limit", default="50", help="auto-adjust limit per item, every currency")
    ap.add_argument("--cycle-cap", default="100", help="auto-adjust cap per cycle, every currency")
    ap.add_argument("--fx-tolerance-pct", default="1.0")
    ap.add_argument("--format", choices=("table", "json"), default="table")
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return int(e.code or 0)
    try:
        invoices, txns = load_ledger(a.ledger), load_txns(a.txns)
        as_of = date.fromisoformat(a.as_of)
        cur = {i.currency for i in invoices} | {t.currency for t in txns}
        policy = Policy(item_limit={c: Decimal(a.item_limit) for c in cur}, cycle_cap={c: Decimal(a.cycle_cap) for c in cur},
                        fx_tolerance_pct=Decimal(a.fx_tolerance_pct))
    except (OSError, InputError, ValueError, ArithmeticError) as e:
        print("input error: %s" % e, file=sys.stderr)
        return 2
    ex, store, audit, appr = new_runtime({i.counterparty: "ben-" + i.id for i in invoices})
    r = run_cycle("USER-%s" % as_of.isoformat(), as_of, invoices, txns, policy, ex, store, audit, appr)
    if a.format == "json":
        rows = [{"subject": d.subject_id, "mismatch": d.finding.mismatch.value, "rule": d.rule_id, "action": d.action.value,
                 "outcome": o, "amount": "%.2f" % d.amount, "currency": d.currency, "evidence": list(d.finding.txn_ids),
                 "reason": d.reason} for d, o in r.outcomes]
        print(json.dumps({"label": "USER-SUPPLIED", "as_of": a.as_of, "decisions": rows}, indent=2))
    else:
        print("== reconcile: USER-SUPPLIED ledger %s + transactions %s (as of %s; no network, refunds to a FAKE gateway) =="
              % (a.ledger, a.txns, a.as_of))
        _print_table(r)
        for d, o in r.outcomes:
            if d.action.value != "NONE":
                print("  %s: %s" % (d.subject_id, d.reason))
    return 0


def cmd_scenes() -> int:
    from closer.adapters.scenes import build_scenes, render_markdown
    print(render_markdown(build_scenes()))
    return 0


def cmd_card() -> int:
    from closer.adapters.card_html import render_card
    invoices, txns, as_of, policy = scenario_pack()
    ex, store, audit, appr = new_runtime({i.counterparty: "ben-" + i.id for i in invoices})
    r = run_cycle("CARD", as_of, invoices, txns, policy, ex, store, audit, appr)
    card = next(d.card for d, o in r.outcomes if o == "PENDING_APPROVAL")
    os.makedirs(DOCS, exist_ok=True)
    path = os.path.join(DOCS, "approval-card.html")
    with open(path, "w") as fh:
        fh.write(render_card(card))
    print("wrote docs/approval-card.html for", card.invoice_id)
    return 0


def cmd_readme() -> int:
    from .readme import build
    with open(os.path.join(ROOT, "README.md"), "w") as fh:
        fh.write(build())
    print("README.md regenerated from README.tmpl.md + metrics + docs/endpoint-log.json")
    return 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "reconcile":
        return cmd_reconcile(argv[1:])
    cmds = {"demo": cmd_demo, "metrics": cmd_metrics, "scenes": cmd_scenes, "card": cmd_card, "live-smoke": cmd_live_smoke, "live-cycle": cmd_live_cycle, "readme": cmd_readme}
    if not argv or argv[0] not in cmds:
        print("usage: python3 -m closer <%s>" % "|".join(sorted(set(cmds) | {"reconcile"})))
        return 2
    return cmds[argv[0]]()
