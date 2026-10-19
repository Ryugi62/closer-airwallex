import dataclasses

import pytest

from closer.domain.approval import ApprovalCard
from closer.domain.signing import ApproverAuthority, Signer
from tests.helpers import D

APPROVER_KEY = b"A" * 32
EXECUTOR_KEY = b"E" * 32


@pytest.fixture
def card():
    return ApprovalCard("REFUND", "INV-1", D("1000.00"), "USD", "Acme Ltd", ("t1", "t2"))


@pytest.fixture
def authority():
    return ApproverAuthority(APPROVER_KEY)


def test_approver_signed_card_verifies(card, authority):
    assert authority.verify(card, authority.sign(card, "cfo"))


def test_card_signed_with_executor_key_is_rejected(card, authority):
    forged = Signer("executor", EXECUTOR_KEY).sign(card, "executor-bot")
    assert not authority.verify(card, forged)


def test_executor_key_cannot_pose_as_approver_role(card, authority):
    forged = Signer("approver", EXECUTOR_KEY).sign(card, "cfo")
    assert not authority.verify(card, forged)


def test_one_byte_change_in_digest_is_rejected(card, authority):
    good = authority.sign(card, "cfo")
    flipped = good.card_digest[:-1] + ("0" if good.card_digest[-1] != "0" else "1")
    assert not authority.verify(card, dataclasses.replace(good, card_digest=flipped))


def test_card_changed_after_signing_is_rejected(card, authority):
    good = authority.sign(card, "cfo")
    assert not authority.verify(dataclasses.replace(card, amount=D("1000.01")), good)
