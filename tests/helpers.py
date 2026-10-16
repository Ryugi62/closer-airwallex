from datetime import date
from decimal import Decimal as D

from closer.domain.models import BankTxn, Direction, Invoice
from closer.domain.policy import Policy

AS_OF = date(2026, 10, 31)


def inv(id="INV-1", amount="1000.00", cur="USD", due=date(2026, 10, 20), cp="Acme Ltd",
        direction=Direction.IN, settle=None, rate=None):
    return Invoice(id=id, direction=direction, counterparty=cp, currency=cur, amount=D(amount),
                   due_date=due, settlement_currency=settle, quoted_rate=D(rate) if rate else None)


def txn(id="ftx_1", amount="1000.00", cur="USD", fee="0", net=None, status="SETTLED",
        desc="payment INV-1", created="2026-10-21T00:00:00+00:00"):
    net = D(amount) - D(fee) if net is None else D(net)
    return BankTxn(id=id, currency=cur, amount=D(amount), fee=D(fee), net=net, status=status,
                   description=desc, created_at=created)


def policy(**kw):
    base = dict(item_limit={"USD": D("50"), "EUR": D("50")}, cycle_cap={"USD": D("200"), "EUR": D("200")},
                fx_tolerance_pct=D("1.0"), rounding_tolerance=D("0.50"))
    base.update(kw)
    return Policy(**base)
