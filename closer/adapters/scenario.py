"""SYNTHETIC scenario pack. Not customer data. Built to exercise every mismatch type."""
from __future__ import annotations

from datetime import date
from decimal import Decimal as D
from typing import List

from closer.domain.models import BankTxn, Direction, Invoice
from closer.domain.policy import Policy

AS_OF = date(2026, 10, 31)
LABEL = "SYNTHETIC scenario pack (not customer data)"


def policy() -> Policy:
    return Policy(item_limit={"USD": D("50")}, cycle_cap={"USD": D("100")},
                  fx_tolerance_pct=D("1.0"), rounding_tolerance=D("0.50"))


def scenario_pack():
    invs: List[Invoice] = []
    txns: List[BankTxn] = []
    n = {"t": 0}

    def invoice(id, amount, cp, cur="USD", due=date(2026, 10, 15), settle=None, rate=None):
        invs.append(Invoice(id, Direction.IN, cp, cur, D(amount), due, settle, D(rate) if rate else None))

    def txn(amount, cur="USD", fee="0", desc="", status="SETTLED"):
        n["t"] += 1
        a, f = D(amount), D(fee)
        txns.append(BankTxn("syn_%04d" % n["t"], cur, a, f, a - f, status, desc, "2026-10-%02dT09:00:00+00:00" % (16 + n["t"] % 14)))

    for k, amt in enumerate(["1200.00", "845.00", "2310.00", "99.00", "4500.00", "310.00", "7800.00", "152.00"], 1):
        invoice("INV-1%02d" % k, amt, "Client %d Ltd" % k)
        txn(amt, desc="payment INV-1%02d" % k)
    for k, (amt, fee) in enumerate([("3300.00", "12.00"), ("1750.00", "18.50"), ("2800.00", "23.50"),
                                    ("1900.00", "30.00"), ("2650.00", "35.00"), ("5100.00", "75.00")], 1):
        invoice("INV-2%02d" % k, amt, "Fee Co %d" % k)
        txn(amt, fee=fee, desc="wire INV-2%02d" % k)
    for k, got in enumerate(["1074.00", "1079.20", "1000.00"], 1):
        invoice("INV-3%02d" % k, "1000.00", "EU Buyer %d" % k, cur="EUR", settle="USD", rate="1.0800")
        txn(got, desc="FX settlement INV-3%02d" % k)
    for k, amt in enumerate(["2500.00", "480.00"], 1):
        invoice("INV-4%02d" % k, amt, "Dup Corp %d" % k)
        txn(amt, desc="payment INV-4%02d" % k)
        txn(amt, desc="payment INV-4%02d resent" % k)
    for k, amt in enumerate(["7300.00", "14100.00", "260.00"], 1):
        invoice("INV-5%02d" % k, amt, "Late Payer %d" % k, due=date(2026, 10, 5))
    for k, amt in enumerate(["8800.00", "21000.00"], 1):
        invoice("INV-6%02d" % k, amt, "Not Due %d" % k, due=date(2026, 11, 20))
    for k, (exp, got) in enumerate([("1500.00", "1499.70"), ("1000.00", "900.00"), ("500.00", "520.00")], 1):
        invoice("INV-7%02d" % k, exp, "Short Pay %d" % k)
        txn(got, desc="payment INV-7%02d" % k)
    invoice("INV-801", "640.00", "Northwind")
    txn("640.00", fee="12.00", desc="wire from northwind")
    txn("412.11", desc="mystery wire 1")
    txn("9999.00", desc="mystery wire 2")
    txn("123.00", desc="payment INV-101 late", status="PENDING")
    return invs, txns, AS_OF, policy()
