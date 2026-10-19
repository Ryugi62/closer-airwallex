# Closer — a reconciliation-close agent on Airwallex

Airwallex's Builder Guide says cash placement and reconciliation are Treasury & Ops jobs "we have not written kits for". Closer takes that gap as an open policy layer that sits on top of the exception queue of tools like Xero and Leapfin: it reads Airwallex financial transactions, matches them to an invoice ledger, classifies every mismatch into one of six types, and then acts: adjust inside limits, hold behind one approval card, or escalate with a stated reason. Every amount, limit, duplicate guard and state transition is plain code with tests. No model is called in the money path today (amount, limit, duplicate and approval decisions); from the build window a model may read free-text evidence, and its output can only become a HOLD.

> Status: a pre-built prototype made for the application, before the official build window. Commits made inside the official build window start on 2026-10-25; the code is frozen until then and only documents change. Public repository URL: added at submission.

> Sandbox only. No real money. The invoice ledger and the scenario pack are SYNTHETIC; the transactions in `live-smoke` / `live-cycle` / `live-deposits` / `live-write` are real Airwallex sandbox (demo environment) data.

## What already exists, and what only Closer has
| Existing | What it does | What it leaves | Only Closer |
|---|---|---|---|
| Airwallex accounting integrations (Xero, QuickBooks, NetSuite) | Hourly sync, automatic match to invoices, "exception-based review" | The non-matching items go to a person | Each leftover item gets a type and a decision: adjust inside limits, hold behind an approval card, or escalate with a reason |
| Airwallex settlement report and Settlements API | Fee file and exchange rate per line | Docs do not cover mismatch handling | Decision layer over the same fields |
| Xero / QuickBooks / Tipalti / JustPerform (GBP 7-115 or USD 20-129 per month) | Suggest matches, user decides | Every exception | Limits, duplicate-refund hold, audit entry with rule id and evidence transaction ids |
| Airwallex and Leapfin (acquisition announced 2026-06-04 in the Airwallex newsroom, opened 2026-10-20) | The release says the companies "plan to launch new product capabilities in the coming months" to simplify reconciliation; I have not tested them | Not launched or not verified | An open, testable policy layer that can sit on top of such an exception queue: every limit and transition is a test; no model in the money path |
| HighRadius cash application (enterprise; vendor product page, opened 2026-10-20) | "Automated GL write-off uses configurable rules to write off items like bank fees, FX, and low-dollar deductions to specific GL accounts" | Items outside the configured limits | Fee, FX and small-difference write-off under limits is not unique to Closer (enterprise tools do it). What Closer adds is open code on Airwallex APIs, and duplicate refunds behind a separate approver-key signature with 0 extra executions in 20 replays |
Eight source types and the full table: `docs/COMPETITORS.md`.

## What it prevents
The riskiest item on the bundled scenario is a duplicate payment: 2,500 USD paid twice. Closer holds the surplus behind one approval card bound to amount, currency, counterparty and evidence, and a replay of the same cycle 20 times causes {{M.replay_extra_executions}} extra executions. The offline demo's 2,500 USD EXECUTED is a fake-gateway scene; the one real sandbox refund (HKD 2,500.00) is still PROCESSING. A spreadsheet exact-match shows the same case only as one more exception.

## The one number
{{METRIC_DEFINITION}}

On the bundled synthetic scenario: {{M.baseline_exceptions}} exceptions with exact match, {{M.closer_human_items}} items for a person with Closer ({{M.roi_items_moved}} fewer, {{M.roi_share_pct}}% of exceptions).

Why {{M.roi_items_moved}} fewer but only {{M.auto_adjusted}} adjusted automatically: the baseline counts an invoice and a bank transaction separately; Closer links one transaction to INV-801 by inference (never auto-adjusted), so those two baseline exceptions become one escalated item. {{M.auto_adjusted}} automatic adjustments + 1 merged pair = {{M.roi_items_moved}}.

## What the part Closer changes is worth (floor, not a measurement)
{{M.roi_items_moved}} items moved off the human queue x {{MIN_PER_ITEM}} minutes x {{KRW_PER_MIN}} KRW per minute (a low floor rate; a finance employee costs more) = {{M.roi_krw_per_cycle}} KRW per cycle on this pack; at the same {{M.roi_share_pct}}% share, {{M.roi_krw_per_1000_exceptions}} KRW per 1,000 exceptions. The minutes per exception is an assumption chosen low; it was not measured at a customer. Assumptions and sources: `docs/APPENDIX.md`.

## When one input changes, the decision changes (generated from real cycles)
{{SCENES}}
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
python3 -m pytest -q          # {{TESTS}} tests, no network
python3 -m closer demo        # full cycle, approval, replay, audit log
```
Tested on Python 3.9.6 (other versions not tested), standard library only (pytest for tests). With sandbox credentials in `AIRWALLEX_CLIENT_ID` / `AIRWALLEX_API_KEY` (or the macOS keychain), `python3 -m closer live-smoke` and `python3 -m closer live-cycle` read the sandbox; `live-deposits` and `live-write` also write to it (simulation deposits, one approved refund transfer) and are never run by the tests.

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
| Decisions that match the hand-written expectation (type and action) | {{M.acc_decision_correct}} of {{M.acc_labelled}} ({{M.acc_decision_accuracy_pct}}%); wrong: {{M.acc_decision_wrong}} |
| Wrong items among the {{M.acc_human_queue_items}} sent to a person | {{M.acc_human_queue_wrong}} |

The expectation is written by hand from SPEC section 4 in `closer/adapters/labels.py`, by the same author as the pack: it shows Closer agrees with its own spec on {{M.acc_labelled}} synthetic cases, not accuracy on real customer data (not measured).

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
- Writes go only to the sandbox (demo environment). One refund transfer (`POST /api/v1/transfers/create`) was executed after an approval card, and the request id is in `docs/live-write-*.json`; its beneficiary is a sandbox fixture named like the payer, not the simulated payer's bank. That one-off write was approved by an operator command, not by a customer; since then the approval is an HMAC-SHA256 signature made with a separate approver key (SPEC section 8): the executor side only verifies, a card signed with the executor key or with a one-byte-different digest is rejected as `APPROVAL_SIGNATURE_INVALID` and moves nothing. HMAC is symmetric, so the executor verifies through the approver-side verify call rather than holding the key; an asymmetric scheme (ed25519) would need a new dependency and is not built. The demo mode still sends refunds to a fake gateway and says so.
- The invoice references in the six live deposits were written by me; how often real payers include an invoice id is not measured, and without one Closer escalates instead of adjusting. The ledger is synthetic; a customer export in Xero's format is planned from 10/25.
- Throughput was not measured beyond the bundled pack.
