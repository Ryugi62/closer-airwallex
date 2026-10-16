from closer.adapters.scenario import scenario_pack
from closer.adapters.metrics import compute_metrics


def test_every_remaining_item_has_a_reason_and_fewer_than_baseline():
    m, report = compute_metrics(*scenario_pack())
    assert m["closer_human_items"] < m["baseline_exceptions"]
    assert all(r["reason"] for r in report if r["outcome"] in ("ESCALATED", "PENDING_APPROVAL"))
    assert m["replay_extra_executions"] == 0
