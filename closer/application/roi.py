"""ROI of only the part Closer changes: exceptions that no longer need a person. Pure arithmetic.
Floor assumptions (stated, not measured at a customer): 5 minutes of work per exception, priced at a low
floor rate (10,320 KRW/hour = 172 KRW/minute)."""
from __future__ import annotations

KRW_PER_HOUR = 10320
KRW_PER_MINUTE = KRW_PER_HOUR // 60
MINUTES_PER_ITEM = 5


def roi_krw(baseline_exceptions: int, closer_human_items: int) -> dict:
    moved = max(0, baseline_exceptions - closer_human_items)
    share = (moved / baseline_exceptions) if baseline_exceptions else 0.0
    per_1000 = round(share * 1000)
    return {
        "items_moved": moved,
        "share_pct": "%.1f" % (share * 100),
        "krw_per_cycle": moved * MINUTES_PER_ITEM * KRW_PER_MINUTE,
        "krw_per_1000_exceptions": per_1000 * MINUTES_PER_ITEM * KRW_PER_MINUTE,
    }

METRIC_DEFINITION = (
    "Items for a person: the number of invoices and bank transactions in one cycle that end held for approval or escalated, "
    "counted against the exact-match baseline exceptions (invoice id in the description, equal amount and currency, zero fee) "
    "on the same ledger and the same transactions."
)
