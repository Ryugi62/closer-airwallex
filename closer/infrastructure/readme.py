"""README numbers are generated, not typed. render() is checked against README.md by a test."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

from closer.adapters.metrics import compute_metrics
from closer.adapters.scenario import scenario_pack

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_count() -> int:
    out = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"], cwd=ROOT,
                         capture_output=True, text=True, timeout=120).stdout
    m = re.search(r"(\d+) tests? collected", out) or re.search(r"(\d+) tests?", out.strip().splitlines()[-1])
    return int(m.group(1))


def endpoint_table(log: dict) -> str:
    rows = ["| Endpoint | HTTP | Request/trace id | Items |", "|---|---|---|---|"]
    for c in log["calls"]:
        rows.append("| `%s` | %s | `%s` | %s |" % (c["endpoint"], c["status"], c["request_id"], c["items"]))
    rows.append("")
    rows.append("Log generated %s by `python3 -m closer live-smoke` (file: docs/endpoint-log.json). Distinct endpoints: %d."
                % (log["generated_at"], len({c["endpoint"] for c in log["calls"]})))
    return "\n".join(rows)


def render(template: str, metrics: dict, log: dict, tests: int) -> str:
    out = template.replace("{{ENDPOINT_TABLE}}", endpoint_table(log)).replace("{{TESTS}}", str(tests))
    return re.sub(r"\{\{M\.(\w+)\}\}", lambda m: str(metrics[m.group(1)]), out)


def build() -> str:
    with open(os.path.join(ROOT, "README.tmpl.md")) as fh:
        tmpl = fh.read()
    with open(os.path.join(ROOT, "docs", "endpoint-log.json")) as fh:
        log = json.load(fh)
    m, _ = compute_metrics(*scenario_pack())
    return render(tmpl, m, log, test_count())
