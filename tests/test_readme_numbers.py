import pathlib

from closer.infrastructure.readme import build

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_readme_equals_generated_render():
    assert (ROOT / "README.md").read_text() == build(), "run: python3 -m closer readme"


def test_no_internal_traces_in_submission_text():
    for f in ("README.md", "SPEC.md"):
        t = (ROOT / f).read_text()
        for bad in ("projects/", "[[", "메인 판단", "TODO", "TBD"):
            assert bad not in t, (f, bad)
