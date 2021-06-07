import pytest
from datadog_checks.avi_vantage import AviVantageCheck

from datadog_checks.base.errors import ConfigurationError


def test_missing_url(dd_run_check):
    instance = {}
    check = AviVantageCheck('avi_vantage', {}, [instance])
    with pytest.raises(Exception, match=r'avi_controller_url') as e:
        dd_run_check(check)


def test_bad_entity(dd_run_check):
    instance = {"avi_controller_url": "foo", "entities": ["foo"]}
    check = AviVantageCheck('avi_vantage', {}, [instance])
    with pytest.raises(Exception, match=r'unexpected value; permitted') as e:
        dd_run_check(check)


def test_filters(dd_run_check):
    instance = {"avi_controller_url": "foo", "resource_filters": [{"type": "include", "entity": "serviceengine", "patterns": ['.*'], "property": "name"}]}
    check = AviVantageCheck('avi_vantage', {}, [instance])
    dd_run_check(check)
