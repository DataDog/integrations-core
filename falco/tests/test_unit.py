import pytest

from datadog_checks.falco import FalcoCheck


def test_empty_instance(dd_run_check):
    with pytest.raises(
        Exception,
        match='\nopenmetrics_endpoint\n  Field required',
    ):
        check = FalcoCheck('falco', {}, [{}])
        dd_run_check(check)
