# Closer — a reconciliation-close agent on Airwallex

Airwallex's Builder Guide says cash placement and reconciliation are Treasury & Ops jobs "we have not written kits for". Closer takes that gap as an open policy layer that sits on top of the exception queue of tools like Xero and Leapfin: it reads Airwallex financial transactions, matches them to an invoice ledger, classifies every mismatch into one of six types, and then acts: adjust inside limits, hold behind one approval card, or escalate with a stated reason. Every amount, limit, duplicate guard and state transition is plain code with tests. No model is called anywhere in the decision path.

> Status: a pre-built prototype made for the application, before the official build window. Commits made inside the official build window start on 2026-10-25; the code is frozen until then and only documents change. Public repository URL: added at submission.

> Sandbox only. No real money. The invoice ledger and the scenario pack are SYNTHETIC; the transactions in `live-smoke` / `live-cycle` are read from the real Airwallex sandbox.

## What already exists, and what only Closer has
| Existing | What it does | What it leaves | Only Closer |
|---|---|---|---|
| Airwallex accounting integrations (Xero, QuickBooks, NetSuite) | Hourly sync, automatic match to invoices, "exception-based review" | The non-matching items go to a person | Each leftover item gets a type and a decision: adjust inside limits, hold behind an approval card, or escalate with a reason |
| Airwallex settlement report and Settlements API | Fee file and exchange rate per line | Docs do not cover mismatch handling | Decision layer over the same fields |
| Xero / QuickBooks / Tipalti / JustPerform (GBP 7-115 or USD 20-129 per month) | Suggest matches, user decides | Every exception | Limits, duplicate-refund hold, audit entry with rule id and evidence transaction ids |
| Airwallex T:0 and the Leapfin acquisition (announced 2026-06-04, from a search summary, page not opened) | AI-native close, launch "in the coming months" (search summary) | Details not verified | An open, testable policy layer that can sit on top of such an exception queue: every limit and transition is a test; no model in the decision path |
Eight source types and the full table: `docs/COMPETITORS.md`.

## What it prevents
The riskiest item on the bundled scenario is a duplicate payment: 2,500 USD paid twice. Closer holds the surplus behind one approval card bound to amount, currency, counterparty and evidence, and a replay of the same cycle 20 times causes 0 extra executions. A spreadsheet exact-match shows the same case only as one more exception.

## The one number
Items for a person: the number of invoices and bank transactions in one cycle that end held for approval or escalated, counted against the exact-match baseline exceptions (invoice id in the description, equal amount and currency, zero fee) on the same ledger and the same transactions.

On the bundled synthetic scenario: 21 exceptions with exact match, 13 items for a person with Closer (8 fewer, 38.1% of exceptions).

Why 8 fewer but only 7 adjusted automatically: the baseline counts an invoice and a bank transaction separately; Closer links one transaction to INV-801 by inference (never auto-adjusted), so those two baseline exceptions become one escalated item. 7 automatic adjustments + 1 merged pair = 8.

## What the part Closer changes is worth (floor, not a measurement)
8 items moved off the human queue x 5 minutes x 172 KRW per minute (a low floor rate; a finance employee costs more) = 6880 KRW per cycle on this pack; at the same 38.1% share, 327660 KRW per 1,000 exceptions. The minutes per exception is an assumption chosen low; it was not measured at a customer. Assumptions and sources: `docs/APPENDIX.md`.

## When one input changes, the decision changes (generated from real cycles)
SYNTHETIC scenes (not customer data)

| Scene | Input that changes | Before: decision (rule, evidence) | After: decision (rule, evidence) | Ends as |
|---|---|---|---|---|
| balance: cycle cap headroom | per-currency adjustment cap 100 -> 50 (second 30.00 fee no longer fits) | AUTO_ADJUST / EXECUTED (R-FEE-1; scn_0002) | ESCALATE / ESCALATED (R-CAP-1; scn_0002) | INV-902 ESCALATED |
| deadline: due date passes | as-of date 2026-10-15 -> 2026-10-31 (invoice due 2026-10-20, no payment) | NONE / NO_ACTION (R-OK-2; no txn) | ESCALATE / ESCALATED (R-MISS-1; no txn) | INV-911 ESCALATED |
| evidence: reference present or not | transaction description loses the invoice id (link falls back to inference) | AUTO_ADJUST / EXECUTED (R-FEE-1; scn_0003) | ESCALATE / ESCALATED (R-INF-1; scn_0003) | INV-921 ESCALATED |
| risk: FX drift grows | settled USD 1074.00 -> 1050.00 against the quoted 1080.00 (drift 0.56% -> 2.78%, tolerance 1.0%) | AUTO_ADJUST / EXECUTED (R-FX-1; scn_0004) | ESCALATE / ESCALATED (R-FX-2; scn_0004) | INV-931 ESCALATED |
| approval: a person signs the card | approval card for the surplus 2500.00 USD is approved (before: not yet) | HOLD_FOR_APPROVAL / PENDING_APPROVAL (R-DUP-1; scn_0005, scn_0006) | HOLD_FOR_APPROVAL / EXECUTED (R-DUP-1; scn_0005, scn_0006) | INV-941 CLOSED |

`balance` here is the per-currency cycle cap headroom for automatic adjustments, not the account balance.

## Try your own data
```
python3 -m closer reconcile --ledger tests/fixtures/ledger.csv --txns tests/fixtures/txns.csv --as-of 2026-10-31
python3 -m closer card      # writes docs/approval-card.html (capture: docs/approval-card.png)
```
Ledger columns: `id,direction,counterparty,currency,amount,due_date[,settlement_currency,quoted_rate]`. Transaction columns: `id,currency,amount,fee,status,description,created_at`. Change the files or `--item-limit` / `--cycle-cap` and the decisions change. Refunds go to a fake gateway.

## Run it in 3 minutes (3 commands plus a one-line pytest install, no key needed)
```
git clone <this repo> && cd airwallex-agentic-banking-2026   # (public URL added at submission)
python3 -m pip install pytest
python3 -m pytest -q          # 76 tests, no network
python3 -m closer demo        # full cycle, approval, replay, audit log
```
Python 3.9+, standard library only (pytest for tests). With sandbox credentials in `AIRWALLEX_CLIENT_ID` / `AIRWALLEX_API_KEY` (or the macOS keychain), `python3 -m closer live-smoke` and `python3 -m closer live-cycle` read the sandbox.

## What it does on the bundled scenario (generated values)
| Measure | Value |
|---|---|
| Invoices / transactions | 28 / 28 |
| Items a spreadsheet exact-match leaves as exceptions | 21 |
| Items Closer needs a person for (held + escalated) | 13 |
| Adjusted automatically inside limits | 7 |
| Held behind an approval card | 2 |
| Escalated with a stated reason | 11 |
| Mismatch types exercised | 6 of 6 |
| Replayed the same cycle 20 times: extra executions | 0 |
| Audit entries per cycle (one per decision) | 31 |

Mismatch types: `FEE_DEDUCTED`, `FX_DIFFERENCE`, `DUPLICATE_PAYMENT`, `MISSING_PAYMENT`, `AMOUNT_MISMATCH`, `UNMATCHED_TXN`.

## Airwallex sandbox calls (live, generated)
| Endpoint | HTTP | Request/trace id | Items |
|---|---|---|---|
| `GET /api/v1/balances/current` | 200 | `1e8cb41c06eb42258cf9510cc752fd34` | 46 |
| `GET /api/v1/financial_transactions` | 200 | `9d0df1a59e7f408383e5de9a49d50064` | 5 |
| `GET /api/v1/transfers` | 200 | `d842a51f7c594624ad8211becaab9f35` | 0 |
| `GET /api/v1/global_accounts` | 200 | `e624e31c243c44a7942f753ac9903fcc` | 1 |
| `GET /api/v1/beneficiaries` | 200 | `31af0567deb84aefa2c4efc9dca97824` | 7 |
| `GET /api/v1/deposits` | 200 | `38436ab34f284f0ebb4a39389b548d01` | 0 |
| `GET /api/v1/fx/conversions` | 200 | `2366c55a6eae4e06a236b86cabce650b` | 0 |
| `GET /api/v1/balances/history` | 200 | `a9afeec106ee4d32b265006fbcd938a8` | 5 |

Log generated 2026-10-16T14:31:00+00:00 by `python3 -m closer live-smoke` (file: docs/endpoint-log.json). Distinct endpoints: 8.

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
