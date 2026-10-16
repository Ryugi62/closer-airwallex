import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures"


def run(*args):
    return subprocess.run([sys.executable, "-m", "closer", *args], cwd=ROOT, capture_output=True, text=True, timeout=30)


def base(*extra):
    return ["reconcile", "--ledger", str(FIX / "ledger.csv"), "--txns", str(FIX / "txns.csv"),
            "--as-of", "2026-10-31", "--item-limit", "50", "--cycle-cap", "100", *extra]


def test_reconcile_json_decides_each_row():
    p = run(*base("--format", "json"))
    assert p.returncode == 0, p.stderr
    rows = {r["subject"]: r for r in json.loads(p.stdout)["decisions"]}
    assert rows["A-1"]["mismatch"] == "MATCHED"
    assert rows["A-2"]["action"] == "AUTO_ADJUST" and rows["A-2"]["rule"] == "R-FEE-1"
    assert rows["A-3"]["action"] == "ESCALATE" and rows["A-3"]["mismatch"] == "MISSING_PAYMENT"
    assert rows["t3"]["mismatch"] == "UNMATCHED_TXN" and rows["t3"]["evidence"] == ["t3"]


def test_user_input_changes_the_decision():
    p = run(*base("--format", "json", "--item-limit", "10"))
    rows = {r["subject"]: r for r in json.loads(p.stdout)["decisions"]}
    assert rows["A-2"]["action"] == "ESCALATE"


def test_table_output_labels_input_as_user_supplied():
    p = run(*base())
    assert p.returncode == 0 and "USER-SUPPLIED" in p.stdout and "A-2" in p.stdout


def test_missing_file_is_a_clear_error_not_a_traceback():
    p = run("reconcile", "--ledger", "nope.csv", "--txns", "nope2.csv")
    assert p.returncode == 2 and "Traceback" not in p.stderr and "nope.csv" in p.stderr


def test_bad_row_names_the_line():
    bad = ROOT / "out" / "bad_txns.csv"
    bad.parent.mkdir(exist_ok=True)
    bad.write_text("id,currency,amount,fee,status,description,created_at\nx1,USD,abc,0,SETTLED,d,2026-10-12\n")
    p = run("reconcile", "--ledger", str(FIX / "ledger.csv"), "--txns", str(bad))
    assert p.returncode == 2 and "line 2" in p.stderr and "Traceback" not in p.stderr
