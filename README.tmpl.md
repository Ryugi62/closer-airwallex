# Closer — a reconciliation-close agent on Airwallex

Airwallex's Builder Guide says cash placement and reconciliation are Treasury & Ops jobs "we have not written kits for". Closer takes that gap: it reads Airwallex financial transactions, matches them to an invoice ledger, classifies every mismatch into one of six types, and then acts: adjust inside limits, hold behind one approval card, or escalate with a stated reason. Every amount, limit, duplicate guard and state transition is plain code with tests. No model is called anywhere in the decision path.

> Sandbox only. No real money. The invoice ledger and the scenario pack are SYNTHETIC; the transactions in `live-smoke` / `live-cycle` are read from the real Airwallex sandbox.

## Run it in 3 minutes (3 commands, no key needed)
```
git clone <this repo> && cd airwallex-agentic-banking-2026
python3 -m pytest -q          # {{TESTS}} tests, no network
python3 -m closer demo        # full cycle, approval, replay, audit log
```
Python 3.9+, standard library only (pytest for tests). With sandbox credentials in `AIRWALLEX_CLIENT_ID` / `AIRWALLEX_API_KEY` (or the macOS keychain), `python3 -m closer live-smoke` and `python3 -m closer live-cycle` read the sandbox.

## What it does on the bundled scenario (generated values)
| Measure | Value |
|---|---|
| Invoices / transactions | {{M.invoices}} / {{M.transactions}} |
| Items a spreadsheet exact-match leaves as exceptions | {{M.baseline_exceptions}} |
| Items Closer needs a person for (held + escalated) | {{M.closer_human_items}} |
| Adjusted automatically inside limits | {{M.auto_adjusted}} |
| Held behind an approval card | {{M.held}} |
| Escalated with a stated reason | {{M.escalated}} |
| Mismatch types exercised | {{M.mismatch_types_seen}} of 6 |
| Replayed the same cycle 20 times: extra executions | {{M.replay_extra_executions}} |
| Audit entries per cycle (one per decision) | {{M.audit_entries}} |

Mismatch types: `FEE_DEDUCTED`, `FX_DIFFERENCE`, `DUPLICATE_PAYMENT`, `MISSING_PAYMENT`, `AMOUNT_MISMATCH`, `UNMATCHED_TXN`.

## Airwallex sandbox calls (live, generated)
{{ENDPOINT_TABLE}}

## How decisions are made
- Matching: invoice id found in the transaction description (`REFERENCE`) or a unique same-direction, same-currency candidate within 5% (`INFERRED`). An inferred link is never auto-adjusted.
- `AUTO_ADJUST` only if the amount is within the per-item limit, the per-currency cycle cap is not exceeded and (for FX) drift is within tolerance.
- `HOLD_FOR_APPROVAL` for duplicate payments: a refund proposal bound to amount, currency, counterparty and evidence transaction ids. Change any of the four after approval and the approval is rejected.
- `ESCALATE` for everything else, with the rule id and reason in the audit log.
- Idempotency: each decision has a key; a key executes once. Replays are skipped and audited.
- A model may be plugged in through the `Explainer` port to word an exception. It cannot change an amount or an action (checked by an import test on `domain/` and `application/`).

## Layout
`closer/domain` (rules, no I/O) <- `closer/application` (use case, ports) <- `closer/adapters` (Airwallex HTTP gateway, fakes, scenario) <- `closer/infrastructure` (CLI, keychain). `SPEC.md` has the numeric success conditions; each maps to a test.

## Honest limits
- The scenario pack and ledger are synthetic. The Airwallex sandbox holds only five funding adjustments, so live mode reads real transaction ids and runs them against a synthetic ledger.
- The refund transfer (`POST /api/v1/transfers/create`) is implemented and unit-tested against a recorded transport, and is not executed live in this version; the demo sends refunds to a fake gateway and says so.
- Throughput was not measured beyond the bundled pack.
