import pytest

from closer.domain.state import IllegalTransition, InvoiceState as S, transition


def test_legal_path():
    s = transition(S.OPEN, S.HELD)
    s = transition(s, S.ADJUSTED)
    assert transition(s, S.CLOSED) == S.CLOSED


@pytest.mark.parametrize("a,b", [(S.CLOSED, S.ADJUSTED), (S.MATCHED, S.HELD), (S.OPEN, S.CLOSED), (S.ESCALATED, S.OPEN)])
def test_illegal(a, b):
    with pytest.raises(IllegalTransition):
        transition(a, b)
