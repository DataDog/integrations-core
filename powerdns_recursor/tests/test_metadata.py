# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import mock
import pytest

from datadog_checks.base.utils.http_exceptions import HTTPTimeoutError
from datadog_checks.base.utils.http_testing import MockHTTPResponse
from datadog_checks.powerdns_recursor import PowerDNSRecursorCheck

from . import common


def _make_check():
    version = common._get_pdns_version()
    if version == 3:
        instance = common.CONFIG
    elif version == 4:
        instance = common.CONFIG_V4
    check = PowerDNSRecursorCheck("powerdns_recursor", {}, [instance])
    check.check_id = 'test:123'
    check.log = mock.MagicMock()
    config_obj, _ = check._get_config(instance)
    return check, config_obj


def test_metadata_unit_timeout(datadog_agent, mock_http):
    check, config_obj = _make_check()
    mock_http.get.side_effect = HTTPTimeoutError('')
    check._collect_metadata(config_obj)
    datadog_agent.assert_metadata_count(0)
    check.log.debug.assert_called_with('Error collecting PowerDNS Recursor version: %s', '')


def test_metadata_unit_missing_header(datadog_agent, mock_http):
    check, config_obj = _make_check()
    mock_http.get.return_value = MockHTTPResponse()
    check._collect_metadata(config_obj)
    datadog_agent.assert_metadata_count(0)
    check.log.debug.assert_called_with("Couldn't find the PowerDNS Recursor Server version header")


def test_metadata_unit_bad_version_header(datadog_agent, mock_http):
    check, config_obj = _make_check()
    mock_http.get.return_value = MockHTTPResponse(headers={'Server': 'wrong_stuff'})
    check._collect_metadata(config_obj)
    datadog_agent.assert_metadata_count(0)
    check.log.debug.assert_called_with('Error while decoding PowerDNS Recursor version: %s', 'list index out of range')


@pytest.mark.usefixtures('dd_environment')
def test_metadata_integration(aggregator, datadog_agent):
    version = common._get_pdns_version()
    if version == 3:
        check = PowerDNSRecursorCheck("powerdns_recursor", {}, [common.CONFIG])
        check.check_id = 'test:123'
        check.check(common.CONFIG)
    elif version == 4:
        check = PowerDNSRecursorCheck("powerdns_recursor", {}, [common.CONFIG_V4])
        check.check_id = 'test:123'
        check.check(common.CONFIG_V4)

    major, minor, patch = common.POWERDNS_RECURSOR_VERSION.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': common.POWERDNS_RECURSOR_VERSION,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(len(version_metadata))
