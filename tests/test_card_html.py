import pathlib
import subprocess
import sys
from decimal import Decimal

from closer.adapters.card_html import render_card
from closer.domain.approval import ApprovalCard

ROOT = pathlib.Path(__file__).resolve().parents[1]


def card(**kw):
    base = dict(action="REFUND_SURPLUS", invoice_id="INV-401", amount=Decimal("2500.00"), currency="USD",
                counterparty="Dup Corp 1", evidence_txn_ids=("syn_0017", "syn_0018"))
    base.update(kw)
    return ApprovalCard(**base)


def test_card_shows_the_four_bound_items_and_digest():
    h = render_card(card())
    for needle in ("2500.00", "USD", "Dup Corp 1", "syn_0017", "syn_0018", card().digest()[:16], "SYNTHETIC"):
        assert needle in h
    assert 'data-bound="amount"' in h and 'data-bound="currency"' in h
    assert 'data-bound="counterparty"' in h and 'data-bound="evidence"' in h


def test_changing_any_bound_item_changes_the_digest_shown():
    base = render_card(card())
    for kw in (dict(amount=Decimal("2500.01")), dict(currency="EUR"), dict(counterparty="Other"),
               dict(evidence_txn_ids=("syn_0017",))):
        assert render_card(card(**kw)) != base


def test_html_escapes_counterparty():
    assert "<script>" not in render_card(card(counterparty="<script>x</script>"))


def test_cli_card_writes_file():
    p = subprocess.run([sys.executable, "-m", "closer", "card"], cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert p.returncode == 0 and (ROOT / "docs" / "approval-card.html").exists()
