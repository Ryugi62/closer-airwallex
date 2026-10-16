# Closer — a reconciliation-close agent on Airwallex

Airwallex's Builder Guide says cash placement and reconciliation are Treasury & Ops jobs "we have not written kits for". Closer takes that gap: it reads Airwallex financial transactions, matches them to an invoice ledger, classifies every mismatch into one of six types, and then acts: adjust inside limits, hold behind one approval card, or escalate with a stated reason. Every amount, limit, duplicate guard and state transition is plain code with tests. No model is called anywhere in the decision path.

> Sandbox only. No real money. The invoice ledger and the scenario pack are SYNTHETIC; the transactions in `live-smoke` / `live-cycle` are read from the real Airwallex sandbox.

## Run it in 3 minutes (3 commands, no key needed)
```
git clone <this repo> && cd airwallex-agentic-banking-2026
python3 -m pytest -q          # 52 tests, no network
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
