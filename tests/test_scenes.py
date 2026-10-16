import subprocess
import sys
import pathlib

from closer.adapters.scenes import INPUT_KINDS, build_scenes, render_markdown

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_four_input_kinds_each_flip_the_decision():
    scenes = build_scenes()
    assert {s.input_kind for s in scenes} >= set(INPUT_KINDS) and len(INPUT_KINDS) == 4
    for s in scenes:
        assert s.before.action != s.after.action or s.before.outcome != s.after.outcome, s.name
        assert s.after.ref and s.before.ref, s.name


def test_every_scene_ends_in_a_transaction_id_or_state():
    for s in build_scenes():
        assert s.after.ref.startswith(("scn_", "INV-")), s.name
        assert s.after.state in {"CLOSED", "ESCALATED", "HELD", "OPEN"}, s.name


def test_markdown_is_labelled_synthetic_and_stable():
    md = render_markdown(build_scenes())
    assert "SYNTHETIC" in md and md == render_markdown(build_scenes())
    assert md.count("\n|") >= 6


def test_cli_scenes_runs():
    p = subprocess.run([sys.executable, "-m", "closer", "scenes"], cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert p.returncode == 0 and "balance" in p.stdout and "deadline" in p.stdout
