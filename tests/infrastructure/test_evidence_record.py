from types import SimpleNamespace

from closer.infrastructure.cli import evidence_record


def test_record_has_model_and_result_but_no_key_fields():
    d = SimpleNamespace(rule_id="R-EVD-1", action=SimpleNamespace(value="HOLD_FOR_APPROVAL"), reason="quote found")
    rec = evidence_record("INV-203", "we dispute", "claude-haiku-4-5", d, "PENDING_PERSON_REVIEW", 0, "20261029T000000Z")
    assert rec["model"] == "claude-haiku-4-5" and rec["rule"] == "R-EVD-1" and rec["transfers_sent"] == 0
    assert not any("key" in k.lower() for k in rec)
