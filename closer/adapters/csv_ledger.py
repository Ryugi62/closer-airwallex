from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from typing import List

from closer.domain.models import BankTxn, Direction, Invoice


class InputError(ValueError):
    """A user-supplied file could not be read; the message names the file and line."""


def load_ledger(path: str) -> List[Invoice]:
    out = []
    with open(path, newline="") as fh:
        for n, r in enumerate(csv.DictReader(fh), 2):
            try:
                out.append(_invoice(r))
            except (KeyError, ValueError, ArithmeticError) as e:
                raise InputError("%s line %d: %s %s" % (path, n, type(e).__name__, e))
    return out


def load_txns(path: str) -> List[BankTxn]:
    out = []
    with open(path, newline="") as fh:
        for n, r in enumerate(csv.DictReader(fh), 2):
            try:
                amt, fee = Decimal(r["amount"]), Decimal(r.get("fee") or "0")
                net = Decimal(r["net"]) if r.get("net") else amt - fee
                out.append(BankTxn(r["id"], r["currency"], amt, fee, net, r["status"].strip().upper(),
                                   r.get("description", ""), r.get("created_at", "")))
            except (KeyError, ValueError, ArithmeticError) as e:
                raise InputError("%s line %d: %s %s" % (path, n, type(e).__name__, e))
    return out


def _invoice(r) -> Invoice:
    return Invoice(
        id=r["id"], direction=Direction(r["direction"]), counterparty=r["counterparty"],
        currency=r["currency"], amount=Decimal(r["amount"]), due_date=date.fromisoformat(r["due_date"]),
        settlement_currency=r.get("settlement_currency") or None,
        quoted_rate=Decimal(r["quoted_rate"]) if r.get("quoted_rate") else None)
