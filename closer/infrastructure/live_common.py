"""Shared helpers for the marked live scenes (sandbox only)."""
from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, List, Set


def wait_for_new(gw: Any, before: Set[str], count: int, sleep: Callable[[float], None], attempts: int) -> List[Any]:
    """Poll until `count` transactions not in `before` are visible and settled (or attempts run out)."""
    new: List[Any] = []
    for _ in range(attempts):
        new = [t for t in gw.list_transactions() if t.id not in before]
        if len(new) >= count and all(t.settled for t in new):
            break
        sleep(2)
    return new


def last_call(gw: Any, endpoint: str) -> Dict[str, Any]:
    return next(c for c in reversed(gw.call_log) if c["endpoint"] == endpoint)


def save(log: Dict[str, Any], out_dir: str, name: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    log["path"] = os.path.join(out_dir, name)
    with open(log["path"], "w") as fh:
        json.dump(log, fh, indent=2)
