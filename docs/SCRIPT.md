# Demo day script, 5 minutes (English, draft v1, about 600 words)
The video is a TTS narration with subtitles; the presenter does not speak live.
Status: draft. Not yet rehearsed by the presenter. Every number below is read from `python3 -m closer metrics` at the time of writing; re-check before recording.

**0:00 - Hook (20 s)**
A small business that gets paid in several currencies closes its books by hand. Airwallex says it has not written kits for reconciliation. So I built one that does the boring part and refuses to do the dangerous part.

**0:20 - What it is (30 s)**
Closer reads Airwallex transactions, matches them to an invoice ledger, names every mismatch, and decides: adjust, hold for one approval, or escalate. Amounts, limits, duplicate guards and state transitions are plain code with tests. No model is called in the decision path.

**0:50 - The number (30 s)**
Items for a person: the number of invoices and bank transactions in one cycle that end held for approval or escalated, counted against the exact-match baseline exceptions (invoice id in the description, equal amount and currency, zero fee) on the same ledger and the same transactions.
On the bundled synthetic scenario a spreadsheet exact-match leaves 21 exceptions. Closer leaves 13 for a person, and every one has a stated reason. Seven were adjusted inside limits, two are held behind approval cards.

**1:20 - Live: the cycle (60 s)**
Run `python3 -m closer demo`. Show the table. Point at a fee-deducted invoice: 23.50 USD, inside the 50 USD item limit, adjusted, audit entry with rule R-FEE-1 and the transaction id. Point at an FX item: drift 0.56 percent, inside tolerance, adjusted; another at 2.78 percent: escalated.

**2:20 - Change one input (60 s)**
Run `python3 -m closer scenes`. Same invoice, one input changes: the cycle cap, the due date, whether the reference is present, the FX drift. Each time the decision flips, and each ends in an invoice and transaction id. When the invoice id disappears from the description, the match is only inferred, so Closer will not adjust anything.

**3:20 - The approval card (50 s)**
A duplicate payment: 2,500 USD paid twice. Closer holds a refund of the surplus. Open `docs/approval-card.html`: amount, currency, counterparty, evidence ids. The approval is bound to exactly these four. Change any one after approval and execution is rejected and audited. In this version the refund goes to a fake gateway; the live transfer call is unit-tested against a recorded transport, not executed.

**4:10 - Real Airwallex data and honest limits (30 s)**
`live-smoke` called eight sandbox endpoints, all HTTP 200, logged with trace ids. The sandbox holds five funding adjustments, so the live cycle runs real transaction ids against a synthetic ledger, and everything synthetic is labelled.

**4:40 - Close (20 s)**
Airwallex already syncs and matches. What is left is the exception. Closer decides it, inside limits, with a person where it matters, and shows its work. Thank you.
