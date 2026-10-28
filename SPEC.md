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
- Writes to Airwallex run only in the sandbox (demo environment): one refund/transfer executed after an approval card, with request id recorded; production writes stay out of scope. The refund goes to a pre-existing sandbox beneficiary, not to the simulated payer. The sandbox held 5 funding adjustments before the simulation deposits, so live decisions use a synthetic ledger against real sandbox transactions.
- Sandbox-only simulation deposits (demo environment) are allowed to produce live transactions for the decision cycle.
- Not a general accounting package: no tax, no multi-entity, no bank-statement import beyond Airwallex.

## 7. UI acceptance criteria (UI 수용기준) — approval card page (docs/approval-card.html)
Copied from the house design checklist and made concrete for one static page:
1. Mobile first: viewport meta, no horizontal scroll at 390 px and 1280 px.
2. One screen, one question: the card asks one thing (approve this refund); one primary action.
3. Type: body >= 16 px, nothing under 12 px, amount line >= 28 px.
4. Spacing: 4/8 px grid, card radius >= 16 px, side gutter >= 16 px.
5. Primary button full width, height >= 52 px; every touch target >= 44 px.
6. Number first: the amount is the first large element.
7. Evidence visible, not hidden: the four bound items and digest prefix are on the card.
8. Microcopy: active voice; the warning says what happens and why (approval rejected, audited).
9. Color: text contrast >= 4.5:1 in light and dark; one brand color; no information by color alone.
10. No external fonts or scripts; page is static. Check: `python3 _system/ui_audit.py docs/approval-card.html` (0 fail).

## 8. Approver / executor key separation (승인자·실행자 분리)
Purpose: until now the approval was a bare digest produced by whoever ran the cycle, so "who approved" and "who executes" were the same process. An approval is now a signed object: the approver signs the card digest with the **approver key**, and the executor side only checks that signature before it moves any money. The executor never holds the approver key and signs nothing as an approver; a card signed with the executor key, or any card whose digest changed by one byte, is rejected with outcome `APPROVAL_SIGNATURE_INVALID` and the transfer gateway is not called. Signatures are HMAC-SHA256 from the Python standard library (no new dependency; the repo is standard-library only). HMAC is symmetric, so the executor checks through the approver-side `ApproverAuthority.verify` callable instead of holding the key; moving to an asymmetric scheme (ed25519) is a later change that needs a new dependency. Keys are generated locally per run and never written to the repo, logs or output.
Role and key names: **ApproverKey**, **ExecutorKey**, **SignedApproval** (card digest, approver name, role, signature), **ApproverAuthority**.

Given / When / Then
1. Given a held refund card and a SignedApproval signed with the approver key. When execution is attempted through the executor-side verifier. Then the signature verifies and the refund executes exactly once.
2. Given the same card signed with the executor key (role `executor`). When execution is attempted. Then it is rejected as `APPROVAL_SIGNATURE_INVALID` and the gateway is not called.
3. Given an approver-signed approval whose card digest is changed by one byte. When execution is attempted. Then it is rejected as `APPROVAL_SIGNATURE_INVALID` and the gateway is not called.
Verified by: tests/domain/test_signing.py, tests/application/test_signed_execution.py, tests/test_cli_demo.py.

## 9. Model evidence reading (모델 증거 읽기) — build window
Purpose: payers and operators send free text ("we already paid this twice, please refund one", "fee note: bank took 23.50"). A model may read that text and extract **facts**. Facts can only make a decision *stricter*: the output of the reading is `HOLD_FOR_APPROVAL` for a person, never an execution. The model never sees amounts to decide with, never picks an action, and never produces a card.
Ubiquitous language: **EvidenceText** (raw free text tied to one subject id), **EvidenceFacts** (claim type, optional amount, currency, promised date, verbatim quote), **EvidenceReader** (port: text in, raw model reply out), **EvidenceReading** (facts or a failure reason), rule ids `R-EVD-1` (evidence disputes or asks refund), `R-EVD-2` (evidence figure disagrees with the ledger), `R-EVD-3` (reading unusable: fail closed).
Rules
- The only schema the reply may fill: `claim` in {DISPUTE, REFUND_REQUEST, PAYMENT_CLAIMED, PROMISE_TO_PAY, FEE_NOTE, OTHER}, `amount`, `currency`, `promised_date`, `quote`. Any other key (for example `action`) is ignored.
- A `quote` that is not a substring of the evidence text (whitespace and case normalised) makes the reading unusable (guards against invented facts and injected instructions).
- Evidence can turn `AUTO_ADJUST` or `NONE` into `HOLD_FOR_APPROVAL`; it can never turn `HOLD_FOR_APPROVAL` or `ESCALATE` into anything less strict, and never produces `AUTO_ADJUST`, `EXECUTED` or an `ApprovalCard`.
- A held-by-evidence decision has no card, so it is never executable (outcome `PENDING_PERSON_REVIEW`).
- A reader failure (no key, network, bad JSON) on a subject that has evidence text fails closed to `R-EVD-3` HOLD; the CLI says plainly when the key is missing.

Given / When / Then
1. Given an `AUTO_ADJUST` fee decision (23.50 USD) and evidence "Please refund, we dispute this fee" read as DISPUTE. When the cycle runs with the reader. Then action `HOLD_FOR_APPROVAL`, rule `R-EVD-1`, executor called 0 times, evidence quote in the audit explanation.
2. Given an `AUTO_ADJUST` decision of 23.50 USD and evidence read as FEE_NOTE amount 23.50 USD. When the cycle runs. Then the decision is unchanged (`AUTO_ADJUST`): agreeing evidence does not promote or demote anything.
3. Given the same decision and evidence read as FEE_NOTE amount 99.00 USD. When the cycle runs. Then `HOLD_FOR_APPROVAL`, rule `R-EVD-2`.
4. Given a model reply with an extra `"action": "AUTO_ADJUST"` key, or a quote not present in the text, or invalid JSON, or a reader that raises. When the cycle runs. Then the extra key is ignored; the other three give `R-EVD-3` HOLD; executor called 0 times.
5. Given a base decision `ESCALATE` or `HOLD_FOR_APPROVAL` (with card). When any evidence is read. Then the decision is returned unchanged (card intact).
6. Given a subject with no evidence text. When the cycle runs. Then the reader is not called and the decision is unchanged.
7. Given no Gemini key. When the Gemini adapter is built. Then it raises `EvidenceKeyMissing` naming where the key is read from, and no request is made.
Verified by: tests/domain/test_evidence.py, tests/application/test_evidence_cycle.py, tests/adapters/test_gemini_evidence.py; S3 (test_architecture.py) still holds: `domain/` and `application/` import no SDK or network module; only `adapters/` talks to Gemini.
Non-goals: the model does not classify mismatches, does not move any amount, and is not called when there is no evidence text. Real model calls are not part of the test suite.

## 10. Late-payment flow (지연·기한 경과 장면) — build window
Purpose: one live-read scene where a delayed transaction and a passed due date end in an escalation to a person. Command: `python3 -m closer late` (`--offline` skips the sandbox read). Ubiquitous language: **anchor transaction** (first settled inbound transaction without fee in the read; a labelled synthetic one if the read has none or is skipped), **Frame** (one cycle run with one changed input).
Honesty rules: the transaction id, currency and amount are real only when read from the sandbox; the invoice `LATE-1` and its due date are SYNTHETIC; the delay is SIMULATED (status forced to PENDING) because the sandbox does not produce late transactions on demand. The output header says so. No transfer is ever sent.

Given / When / Then
1. Given an anchor transaction SETTLED and an invoice for the same amount due 2026-11-10, as-of 2026-11-09. When the cycle runs. Then `R-OK-1`, invoice CLOSED.
2. Given the same, transaction status changed to PENDING (delay), as-of unchanged. When the cycle runs. Then `R-OK-2` NONE (not yet due; the pending transaction is excluded), invoice OPEN.
3. Given the same, as-of changed to 2026-11-12. When the cycle runs. Then `R-MISS-1` ESCALATE, invoice ESCALATED, transfers sent 0.
Verified by: tests/test_late_flow.py.
