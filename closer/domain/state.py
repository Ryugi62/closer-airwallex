from __future__ import annotations

from enum import Enum


class InvoiceState(str, Enum):
    OPEN = "OPEN"
    MATCHED = "MATCHED"
    ADJUSTED = "ADJUSTED"
    HELD = "HELD"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


S = InvoiceState
ALLOWED = {
    S.OPEN: {S.MATCHED, S.ADJUSTED, S.HELD, S.ESCALATED},
    S.MATCHED: {S.CLOSED},
    S.ADJUSTED: {S.CLOSED},
    S.HELD: {S.ADJUSTED, S.ESCALATED, S.CLOSED},
    S.ESCALATED: {S.CLOSED},
    S.CLOSED: set(),
}


class IllegalTransition(Exception):
    pass


def transition(current: InvoiceState, new: InvoiceState) -> InvoiceState:
    if new not in ALLOWED[current]:
        raise IllegalTransition("%s -> %s" % (current.value, new.value))
    return new
