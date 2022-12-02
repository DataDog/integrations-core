import pytest


def test_passed():
    assert True


def test_failed():
    assert 1 == 2


@pytest.mark.skip(reason="Skip this test")
def test_skip_this():
    assert True


@pytest.mark.parametrize("num", [1, 2, 3])
def test_passing(num):
    print(num)
    assert True
