import json
import subprocess
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def run(*args):
    return subprocess.run([sys.executable, "-m", "closer", *args], cwd=ROOT, capture_output=True, text=True, timeout=30)


def test_demo_runs_offline_and_prints_synthetic_label():
    p = run("demo")
    assert p.returncode == 0, p.stderr
    assert "SYNTHETIC" in p.stdout and "AUTO_ADJUST" in p.stdout and "HOLD_FOR_APPROVAL" in p.stdout


def test_metrics_json_is_valid_and_has_required_keys():
    p = run("metrics")
    m = json.loads(p.stdout)
    for k in ("invoices", "baseline_exceptions", "closer_human_items", "auto_adjusted", "held", "escalated",
              "mismatch_types_seen", "replay_extra_executions", "audit_entries"):
        assert k in m
    assert m["closer_human_items"] < m["baseline_exceptions"]
    assert m["replay_extra_executions"] == 0
    assert m["mismatch_types_seen"] >= 5
