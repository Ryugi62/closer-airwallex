"""Model evidence reading, domain side. Pure Python: no model, no network.

A model's reply is untrusted text. It is parsed into a fixed set of facts, and facts can only make a
decision stricter (HOLD_FOR_APPROVAL for a person). They never execute anything and never create a card.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Optional

from .decision import Decision
from .models import Action


class Claim(str, Enum):
    DISPUTE = "DISPUTE"
    REFUND_REQUEST = "REFUND_REQUEST"
    PAYMENT_CLAIMED = "PAYMENT_CLAIMED"
    PROMISE_TO_PAY = "PROMISE_TO_PAY"
    FEE_NOTE = "FEE_NOTE"
    OTHER = "OTHER"


@dataclass(frozen=True)
class EvidenceFacts:
    claim: Claim
    amount: Optional[Decimal]
    currency: Optional[str]
    promised_date: Optional[str]
    quote: str


@dataclass(frozen=True)
class EvidenceReading:
    facts: Optional[EvidenceFacts]
    failure: Optional[str] = None


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def _unusable(why: str) -> EvidenceReading:
    return EvidenceReading(None, why)


def parse_reading(raw: str, text: str) -> EvidenceReading:
    """Turn a raw model reply into facts, or a failure reason. Unknown keys are dropped."""
    body = raw.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", body, re.S)
    if fenced:
        body = fenced.group(1)
    try:
        obj = json.loads(body)
    except ValueError:
        return _unusable("reply is not JSON")
    if not isinstance(obj, dict):
        return _unusable("reply is not a JSON object")
    try:
        claim = Claim(str(obj.get("claim", "")).upper())
    except ValueError:
        return _unusable("unknown claim type")
    amount = None
    if obj.get("amount") not in (None, ""):
        try:
            amount = Decimal(str(obj["amount"]))
        except InvalidOperation:
            return _unusable("amount is not a number")
    quote = str(obj.get("quote") or "")
    if not quote.strip() or _norm(quote) not in _norm(text):
        return _unusable("quote is not in the evidence text")
    cur = obj.get("currency")
    pdate = obj.get("promised_date")
    return EvidenceReading(EvidenceFacts(claim, amount, str(cur).upper() if cur else None,
                                         str(pdate) if pdate else None, quote.strip()))


def _hold(d: Decision, rule: str, reason: str) -> Decision:
    return replace(d, action=Action.HOLD_FOR_APPROVAL, rule_id=rule, reason=reason, card=None)


def apply_evidence(d: Decision, reading: EvidenceReading) -> Decision:
    """Stricter-only: HOLD and ESCALATE pass through unchanged; AUTO_ADJUST/NONE may become a card-less HOLD."""
    if d.action in (Action.HOLD_FOR_APPROVAL, Action.ESCALATE):
        return d
    if reading.facts is None:
        return _hold(d, "R-EVD-3", "evidence could not be read (%s); a person reads the original text" % reading.failure)
    f = reading.facts
    if f.claim in (Claim.DISPUTE, Claim.REFUND_REQUEST):
        return _hold(d, "R-EVD-1", 'evidence %s: "%s"; a person decides' % (f.claim.value, f.quote))
    if f.amount is not None and f.claim in (Claim.FEE_NOTE, Claim.PAYMENT_CLAIMED):
        if (f.currency and f.currency != d.currency) or abs(abs(f.amount) - d.amount) > Decimal("0.01"):
            return _hold(d, "R-EVD-2", 'evidence figure %s %s disagrees with the ledger %.2f %s: "%s"'
                         % (f.amount, f.currency or "", d.amount, d.currency, f.quote))
    return d
