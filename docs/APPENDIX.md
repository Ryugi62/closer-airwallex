# Appendix

## A. Metric definition (same sentence as README and the script)
Items for a person: the number of invoices and bank transactions in one cycle that end held for approval or escalated, counted against the exact-match baseline exceptions (invoice id in the description, equal amount and currency, zero fee) on the same ledger and the same transactions.

Baseline = what a spreadsheet exact-match leaves: an invoice is clean only if exactly one settled transaction names its id with equal amount, equal currency and zero fee; unmatched settled transactions and past-due invoices without payment are exceptions. Code: `closer/adapters/metrics.py`, value: `python3 -m closer metrics`.

## B. ROI of the part Closer changes
items moved off the human queue = baseline exceptions - items for a person. Value = items moved x 5 minutes x 172 KRW/minute.
- 172 KRW/minute = 10,320 KRW/hour / 60. 10,320 is the 2026 statutory minimum hourly wage; confirmed only through secondary sources (e.g. https://www.bizforms.co.kr/365guide/view.asp?number=162, https://thecheck.co.kr/?p=4669), not the Ministry of Employment and Labor notice. It is a floor: a finance employee costs more.
- 5 minutes per exception is an assumption, chosen low. No source; not measured at a customer. Sensitivity: 10 minutes doubles the value, 2 minutes scales it by 0.4.
- The share of exceptions moved (38.1% here) comes from a synthetic pack built to exercise every mismatch type, so it is not a forecast for a real ledger. Throughput beyond the pack was not measured.
- Code and tests: `closer/application/roi.py`, `tests/test_roi.py`. Numbers in README are generated from the same function.

## C. Where Closer's numbers come from
- Tests: `python3 -m pytest -q`. Scenes: `python3 -m closer scenes`. Approval card: `docs/approval-card.html`, capture `docs/approval-card.png`. Live reads: `docs/endpoint-log.json`.
