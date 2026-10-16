# SPEC — Closer: a reconciliation-close agent on Airwallex

Status: v1 (2026-10-16). Hackathon: Agentic Banking Hackathon (Airwallex x HackerEarth). Sandbox only, no real money.

## 1. Purpose (목적)
A small multi-currency business receives and pays money all month and closes the books by hand against an invoice ledger. Airwallex's own Builder Guide says: "Cash placement and reconciliation are Treasury & Ops jobs too, and we have not written kits for them."

Closer reads Airwallex financial transactions, matches them to an invoice ledger, classifies every mismatch by type, and decides per mismatch: adjust automatically, hold for a person's approval, or escalate. Amounts, limits, duplicate protection and state transitions live in deterministic code. No LLM is called in domain or application code. A model, if plugged in, may only write the plain-language explanation of an exception.

The change in outcome: an item that a spreadsheet exact-match leaves as an "exception" is either closed with an audit trail, held behind a single approval card, or escalated with a stated reason.

## 2. Ubiquitous language (code names match)
- **Invoice**: ledger line with id, direction (IN or OUT), counterparty, currency, amount (gross, major units), due date, optional settlement currency and quoted rate.
- **BankTxn**: Airwallex financial transaction (id, currency, amount, fee, net, status, description, created_at).
- **Link**: BankTxn to Invoice association. `REFERENCE` (invoice id appears in description) or `INFERRED` (unique same-direction, same-currency candidate within 5% amount).
- **MismatchType**: `FEE_DEDUCTED`, `FX_DIFFERENCE`, `DUPLICATE_PAYMENT`, `MISSING_PAYMENT`, `AMOUNT_MISMATCH`, `UNMATCHED_TXN`. A clean match is `MATCHED` (no mismatch).
- **Action**: `AUTO_ADJUST`, `HOLD_FOR_APPROVAL`, `ESCALATE`, `NONE`.
- **Policy**: per-item auto-adjust limit per currency, per-cycle cap per currency, fee tolerance, FX tolerance percent, rounding tolerance.
- **ApprovalCard**: the exact thing a person approves; bound to amount, currency, counterparty, evidence txn ids.
- **IdempotencyKey**: hash of invoice id, mismatch type, evidence txn ids, amount. One key executes at most once.
- **AuditEntry**: one row per decision (cycle id, invoice id or txn id, mismatch type, rule id, evidence txn ids, action, outcome).
- **Cycle**: one reconciliation run over a ledger and a transaction window.

## 3. Numeric success conditions (성공 조건; each is a test or a generated value)
| # | Condition | Verified by |
|---|---|---|
| S1 | >= 5 mismatch types classified; each type has >= 1 test (target 6) | tests/domain/test_classify.py |
| S2 | Replaying the same cycle 20 times causes 0 additional executions after the first run | tests/application/test_idempotency.py |
| S3 | 0 LLM or network imports in `domain/` and `application/` | tests/test_architecture.py |
| S4 | Changing any of amount, currency, counterparty, evidence of a held action after approval invalidates the approval (4 of 4 changes rejected) | tests/domain/test_approval.py |
| S5 | Over 500 randomized cases: executed auto-adjustment per item <= item limit and sum per currency <= cycle cap, 500 of 500 | tests/domain/test_policy_property.py |
| S6 | 100% of decisions produce an audit entry containing rule id and >= 1 id (invoice or txn) | tests/application/test_audit.py |
| S7 | >= 6 distinct Airwallex sandbox endpoints called live, each logged with HTTP status and request id, README table generated from the log | `python3 -m closer live-smoke`, docs/endpoint-log.json |
| S8 | On the bundled scenario pack, closer leaves strictly fewer items for a human than the exact-match baseline, and every remaining item has a stated reason | tests/test_metrics.py, docs/metrics.json |
| S9 | Demo runs offline in <= 10 s with <= 3 setup commands, no key needed | README, tests/test_cli_demo.py |
| S10 | Every number in README is generated from a run (docs/metrics.json); mismatch between README and metrics = test failure | tests/test_readme_numbers.py |
| S11 | No state transition outside the allowed table (illegal transition raises) | tests/domain/test_state.py |

## 4. Behaviour (Given / When / Then)
1. Given an IN invoice 1,000.00 USD and a SETTLED txn amount 1,000.00 fee 0, referencing the invoice id. When the cycle runs. Then classification is MATCHED, action NONE, invoice state MATCHED then CLOSED.
2. Given an IN invoice 1,000.00 USD and a txn amount 1,000.00 fee 23.50 net 976.50. When the cycle runs. Then FEE_DEDUCTED, shortfall 23.50 equals fee; if 23.50 <= item limit and cycle cap allows, action AUTO_ADJUST (bank-fee expense entry), else ESCALATE.
3. Given an invoice quoted 1,000.00 EUR settled in USD at quoted rate 1.0800 (expected 1,080.00) and a txn of 1,074.00 USD. When the cycle runs. Then FX_DIFFERENCE with drift 0.56%; within FX tolerance and limit => AUTO_ADJUST (FX loss entry); beyond => ESCALATE.
4. Given one invoice and two SETTLED txns of the same amount both referencing it. When the cycle runs. Then DUPLICATE_PAYMENT, action HOLD_FOR_APPROVAL with a refund proposal for the surplus; nothing executes until a matching approval is presented.
5. Given a HELD refund and an approval produced for a different amount, currency, counterparty or evidence set. When execution is attempted. Then it is rejected and the audit shows `APPROVAL_MISMATCH`.
6. Given an IN invoice past its due date with no txn. When the cycle runs. Then MISSING_PAYMENT, action ESCALATE with a dunning proposal. An invoice not yet due produces no mismatch.
7. Given a txn with no reference and no unique candidate. When the cycle runs. Then UNMATCHED_TXN, action ESCALATE (inbound funds are not allocated to anyone).
8. Given an invoice and a txn smaller by an amount that is not the fee and not FX. When the cycle runs. Then AMOUNT_MISMATCH; <= rounding tolerance => AUTO_ADJUST (rounding), otherwise ESCALATE.
9. Given auto-adjustments whose sum would exceed the per-currency cycle cap. When the cycle runs. Then the item that would breach the cap is ESCALATED, never executed.
10. Given the same cycle replayed. When it runs again. Then every decision is skipped with outcome `SKIPPED_DUPLICATE` and the executor is not called.
11. Given an INFERRED link with a nonzero difference. When the cycle runs. Then action is never AUTO_ADJUST (ESCALATE) because the link itself is uncertain.
12. Given a txn whose status is not SETTLED. When the cycle runs. Then it is excluded from matching and audited as `SKIPPED_NOT_SETTLED`.

## 5. Architecture (Clean, dependencies point inward)
`closer/domain` (Money, models, classifier, policy, decision, state machine, approval, idempotency key; pure Python, no I/O) <- `closer/application` (ports, run_cycle use case, audit, metrics) <- `closer/adapters` (Airwallex HTTP gateway, in-memory fake gateway, JSON stores, scenario pack, template explainer) <- `closer/infrastructure` (CLI, keychain reader, composition root).

## 6. Non-goals (비목표)
- No model training. No real money. No production credentials.
- No claim that the bundled scenario pack is real customer data: it is synthetic and labelled so everywhere.
- Writes to Airwallex (refund transfer) are implemented in the adapter and unit-tested against a recorded transport; this stage does not execute live writes. The sandbox holds 5 funding adjustments only, so live reads feed the cycle against a synthetic ledger.
- Not a general accounting package: no tax, no multi-entity, no bank-statement import beyond Airwallex.
