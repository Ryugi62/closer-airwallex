from __future__ import annotations

from typing import List, Optional, Protocol

from closer.domain.approval import Approval
from closer.domain.decision import Decision
from closer.domain.models import AuditEntry


class Executor(Protocol):
    def execute(self, decision: Decision) -> str: ...


class KeyStore(Protocol):
    def has(self, key: str) -> bool: ...
    def add(self, key: str) -> None: ...


class AuditSink(Protocol):
    def append(self, entry: AuditEntry) -> None: ...


class ApprovalSource(Protocol):
    def find(self, invoice_id: str) -> Optional[Approval]: ...


class Explainer(Protocol):
    """The only place a model may be used: wording an exception. Never decides."""
    def explain(self, decision: Decision) -> str: ...
