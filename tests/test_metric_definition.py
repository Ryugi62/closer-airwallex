import pathlib

from closer.application.roi import METRIC_DEFINITION

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLACES = ["README.md", "docs/SCRIPT.md", "docs/APPENDIX.md"]


def test_same_definition_sentence_in_readme_script_and_appendix():
    for f in PLACES:
        assert METRIC_DEFINITION in (ROOT / f).read_text(), f


def test_definition_names_unit_and_baseline():
    assert "invoices and bank transactions" in METRIC_DEFINITION and "baseline" in METRIC_DEFINITION


def test_script_and_qa_numbers_match_generated_metrics():
    from closer.adapters.metrics import compute_metrics
    from closer.adapters.scenario import scenario_pack
    m, _ = compute_metrics(*scenario_pack())
    script = (ROOT / "docs" / "SCRIPT.md").read_text()
    qa = (ROOT / "docs" / "QA.md").read_text()
    assert "leaves %d exceptions" % m["baseline_exceptions"] in script
    assert "leaves %d for a person" % m["closer_human_items"] in script
    assert "%d items x 5 minutes x 172 KRW = %s KRW" % (m["roi_items_moved"], format(m["roi_krw_per_cycle"], ",")) in qa
