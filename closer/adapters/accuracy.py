"""Decision accuracy of Closer against labelled expectations. No labels -> null, never an invented number."""
from __future__ import annotations

from typing import Dict, List, Tuple

HUMAN = {"HOLD_FOR_APPROVAL", "ESCALATE"}


def measure_accuracy(report: List[Dict], labels: Dict[str, Tuple[str, str]]) -> Dict:
    rows = [(r, labels[r["subject"]]) for r in report if r["subject"] in labels]
    tw = sum(1 for r, (t, _) in rows if r["mismatch"] != t)
    aw = sum(1 for r, (_, a) in rows if r["action"] != a)
    dw = sum(1 for r, (t, a) in rows if r["mismatch"] != t or r["action"] != a)
    n = len(rows)
    hq = [(r, l) for r, l in rows if r["action"] in HUMAN]
    hw = sum(1 for r, (t, a) in hq if r["mismatch"] != t or r["action"] != a)
    return {"labelled": n, "type_wrong": tw, "type_correct": n - tw, "action_wrong": aw, "action_correct": n - aw,
            "decision_wrong": dw, "decision_correct": n - dw,
            "decision_accuracy_pct": ("%.1f" % (100.0 * (n - dw) / n)) if n else None,
            "human_queue_items": len(hq), "human_queue_wrong": hw}
