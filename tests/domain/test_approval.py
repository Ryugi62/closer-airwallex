import dataclasses

import pytest

from closer.domain.approval import approve, verify
from closer.domain.decision import decide
from closer.domain.classifier import classify
from tests.helpers import AS_OF, D, inv, policy, txn


@pytest.fixture
def card():
    pol = policy()
    invs = [inv()]
    return decide(classify(invs, [txn(id="a"), txn(id="b")], AS_OF, pol), invs, pol)[0].card


def test_matching_approval_verifies(card):
    assert verify(card, approve(card, "cfo"))


@pytest.mark.parametrize("change", [
    {"amount": D("999.00")},
    {"currency": "EUR"},
    {"counterparty": "Other Ltd"},
    {"evidence_txn_ids": ("a", "c")},
])
def test_any_change_invalidates_approval(card, change):
    approval = approve(card, "cfo")
    assert not verify(dataclasses.replace(card, **change), approval)
