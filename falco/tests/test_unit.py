import pytest
from datadog_checks.falco import FalcoCheck


def test_check_initialization():
    check = FalcoCheck('falco', {}, [{}])
    assert isinstance(check, FalcoCheck) 