from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from typing import List

from closer.domain.models import Direction, Invoice


def load_ledger(path: str) -> List[Invoice]:
    out = []
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            out.append(Invoice(
                id=r["id"], direction=Direction(r["direction"]), counterparty=r["counterparty"],
                currency=r["currency"], amount=Decimal(r["amount"]), due_date=date.fromisoformat(r["due_date"]),
                settlement_currency=r.get("settlement_currency") or None,
                quoted_rate=Decimal(r["quoted_rate"]) if r.get("quoted_rate") else None))
    return out
