"""Approver / executor key separation. Pure standard library (hmac); no I/O, no key generation here."""
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass

from .approval import ApprovalCard

APPROVER_ROLE = "approver"


@dataclass(frozen=True)
class SignedApproval:
    card_digest: str
    approver: str
    role: str
    signature: str


def _tag(key: bytes, role: str, card_digest: str) -> str:
    return hmac.new(key, ("%s:%s" % (role, card_digest)).encode(), hashlib.sha256).hexdigest()


class Signer:
    """Holds one key and signs a card for one role. An executor-side Signer is built with role 'executor'."""

    def __init__(self, role: str, key: bytes) -> None:
        self._role, self._key = role, key

    def sign(self, card: ApprovalCard, who: str) -> SignedApproval:
        digest = card.digest()
        return SignedApproval(digest, who, self._role, _tag(self._key, self._role, digest))


class ApproverAuthority(Signer):
    """The approver side. Only this object holds the approver key; the executor is handed `verify` only."""

    def __init__(self, key: bytes) -> None:
        super().__init__(APPROVER_ROLE, key)

    def verify(self, card: ApprovalCard, approval: SignedApproval) -> bool:
        if getattr(approval, "role", None) != APPROVER_ROLE:
            return False
        if approval.card_digest != card.digest():
            return False
        return hmac.compare_digest(approval.signature, _tag(self._key, APPROVER_ROLE, approval.card_digest))
