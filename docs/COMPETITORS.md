# Similar services (researched 2026-10-17)

Framing: Closer is an open policy layer that sits on top of the exception queue of Xero, Leapfin and Airwallex's own accounting integrations. Those tools find and suggest matches; Closer decides what to do with the items they leave.

Question: who already solves "match Airwallex money movement to an invoice ledger and handle the mismatches", and what does Closer have that they do not?
Method: 8 source types tried; result per type below. Search summaries were checked by opening the page where marked "opened".

## Comparison (first-page version is in README)
| # | Service | How it works / price | What it does with a mismatch | Only Closer has |
|---|---|---|---|---|
| 1 | Airwallex integrations for Xero, QuickBooks, NetSuite (own product) | Hourly sync of transactions; "Automatically matches incoming payments to invoices"; "Exception-based review, so your team only handles the transactions that don't match automatically." Price not on the page. | Leaves the non-matching items to the team | Per-item mismatch type (fee, FX, duplicate, missing, amount, unmatched), a limit-bound automatic adjustment, an approval card bound to amount, currency, counterparty and evidence |
| 2 | Airwallex Settlement report / Settlements API (own docs) | Settlement file plus fee file per transaction; exchange-rate field per line | The page "doesn't address how to handle mismatches" (opened) | The decision layer on top of those fields |
| 3 | Airwallex T:0 "Accountant" agent and the Leapfin acquisition (announced 2026-06-04; search summary, page not opened) | AI-native accounting; reconciliation and close promised "in the coming months" (search summary). Not independently tested. | Details not verified | A policy layer that could sit on top of such a queue: open code where every limit and state transition is a test, and a person can read why each item was decided. |
| 4 | Xero bank reconciliation | Simple from GBP 7/month, Grow from GBP 37/month (Airwallex blog); Capterra lists Growing at USD 25/month with the JAX AI feature | Suggests matches; user decides | Policy limits, duplicate refund hold, audit entry with rule id per decision |
| 5 | QuickBooks Online | GBP 33-115/month (Airwallex blog); USD 38-340/month (Capterra summary) | Rule-based matching; user decides | same as above |
| 6 | Tipalti | From USD 129/month (Airwallex blog) | Payables automation | Reconciliation of inbound money against an invoice ledger |
| 7 | insightsoftware JustPerform | Free to 20 reconciliations/month; USD 20 per GL account per month | Account reconciliation workflow | Airwallex transaction reads and the approval-bound refund proposal |
| 8 | BlackLine, NetSuite | Enterprise, quote only (Airwallex blog) | Enterprise close suites | Runs in 3 commands with no key; scope is one function |
| 9 | Hackathon entries: ReconcilAi (lablab.ai, 2024, bank statement and invoice matching; placement not shown), Umbraic (AI Tinkerers, invoice to payment decision) | Demos | Not published | Counting against an exact-match baseline and a replay test (0 extra executions in 20 replays) |

## Source types tried
| Source type | Result | Where |
|---|---|---|
| Vendor site and blog | Found | https://www.airwallex.com/en-uk/blog/best-payment-reconciliation-software-providers (opened) · https://www.airwallex.com/us/bill-pay-integrations |
| Manual / API docs | Found | https://www.airwallex.com/docs/payments/payment-operations/reporting/settlement-report (opened) |
| Job posting | Found | https://jobs.airtree.vc/companies/airwallex/jobs/88180762-manager-financial-operations-reconciliation (opened; posted 2026-07-31): "Manage reconciliation breaks end-to-end, including triage, investigation, root-cause analysis" and "including automation". Airwallex staffs break investigation with people today. |
| News / press release | Found, not opened | https://www.businesswire.com/news/home/20260604721634/en/ (Leapfin acquisition, search summary only; page not opened) |
| Patent | Found related, none identical | https://patents.justia.com/patent/20050075979 (seller-assisted exception management, 2005) · CA 3141627. No patent found that claims fee-deduction or FX-difference classification. Search covered Google-style text only, not claim-level USPTO search. |
| Paper | Found related, none identical | https://arxiv.org/html/2601.15322v1 (Replayable Financial Agents; benchmarks do not include reconciliation). No reconciliation-specific benchmark found. |
| Hackathon entries | Found | https://lablab.ai/submissions/clsw6k5do00003b6w591e9sud · https://aitinkerers.org/hackathons/h_e3M3fuqqAhA/entries/ht_6iadJX9oZoc (via search summaries) |
| Video, government grants | Not tried | no reason to expect a different answer; marked unread |

## Reading
- Airwallex's accounting integrations (rows 1-3) already sync and match, and Closer is built to work on what they leave. The claim "nobody does reconciliation" is false and is not made. The Builder Guide sentence is about starter kits for builders, not about Airwallex products.
- The defensible claim is narrower: the decision on each leftover item is typed, bounded by code, bound to an approval card, and replay-safe, and the repo shows it.
