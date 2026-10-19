from closer.adapters.accuracy import measure_accuracy
from closer.adapters.labels import SCENARIO_LABELS
from closer.adapters.metrics import compute_metrics
from closer.adapters.scenario import scenario_pack


def _report():
    return compute_metrics(*scenario_pack())[1]


def test_labels_cover_every_decision_exactly_once():
    subjects = [r["subject"] for r in _report()]
    assert sorted(subjects) == sorted(SCENARIO_LABELS)


def test_accuracy_on_bundled_pack_counts_wrong_decisions():
    a = measure_accuracy(_report(), SCENARIO_LABELS)
    assert a["labelled"] == 31
    assert a["type_correct"] + a["type_wrong"] == 31
    assert a["action_correct"] + a["action_wrong"] == 31
    assert a["decision_wrong"] == 0 and a["decision_correct"] == 31
    assert a["human_queue_items"] == 13 and a["human_queue_wrong"] == 0


def test_measure_detects_a_wrong_decision():
    rep = [dict(r) for r in _report()]
    for r in rep:
        if r["subject"] == "INV-206":
            r["action"] = "AUTO_ADJUST"
    a = measure_accuracy(rep, SCENARIO_LABELS)
    assert a["decision_wrong"] == 1 and a["action_wrong"] == 1 and a["type_wrong"] == 0


def test_no_labels_reports_null_not_a_number():
    a = measure_accuracy(_report(), {})
    assert a["labelled"] == 0 and a["decision_accuracy_pct"] is None
