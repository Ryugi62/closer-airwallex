from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Dict, List, Optional, Set

from closer.domain.approval import Approval
from closer.domain.decision import Decision
from closer.domain.models import AuditEntry


class RecordingExecutor:
    def __init__(self) -> None:
        self.calls: List[Decision] = []

    def execute(self, decision: Decision) -> str:
        self.calls.append(decision)
        return "mem-%d" % len(self.calls)


class InMemoryKeyStore:
    def __init__(self) -> None:
        self._keys: Set[str] = set()

    def has(self, key: str) -> bool:
        return key in self._keys

    def add(self, key: str) -> None:
        self._keys.add(key)


class ListAuditSink:
    def __init__(self) -> None:
        self.entries: List[AuditEntry] = []

    def append(self, entry: AuditEntry) -> None:
        self.entries.append(entry)


class JsonlAuditSink(ListAuditSink):
    def __init__(self, path: str) -> None:
        super().__init__()
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    def append(self, entry: AuditEntry) -> None:
        super().append(entry)
        with open(self.path, "a") as fh:
            fh.write(json.dumps(asdict(entry), default=str) + "\n")


class InMemoryApprovals:
    def __init__(self) -> None:
        self._by_invoice: Dict[str, Approval] = {}

    def put(self, invoice_id: str, approval: Approval) -> None:
        self._by_invoice[invoice_id] = approval

    def find(self, invoice_id: str) -> Optional[Approval]:
        return self._by_invoice.get(invoice_id)
