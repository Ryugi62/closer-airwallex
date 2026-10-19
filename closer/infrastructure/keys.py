"""Local, per-run key generation for the approver and the executor. Keys live in memory only and are never printed or written."""
from __future__ import annotations

import secrets
from typing import Tuple

from closer.domain.signing import ApproverAuthority, Signer


def new_signing_pair() -> Tuple[ApproverAuthority, Signer]:
    return ApproverAuthority(secrets.token_bytes(32)), Signer("executor", secrets.token_bytes(32))
