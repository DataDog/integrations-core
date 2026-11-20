# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from typing import Any

import mock
import pytest

from datadog_checks.base.stubs.http import FakeHTTPClient, FakeHTTPResponse
from datadog_checks.base.utils.http_exceptions import HTTPClientReadTimeoutError
from datadog_checks.powerdns_recursor import PowerDNSRecursorCheck

from . import common


def _register_metadata_outcome(
    fake_http: FakeHTTPClient, instance: dict[str, Any], outcome: FakeHTTPResponse | Exception
):
    # Version 3 asks the statistics endpoint first and falls back to the v4 API root.
    base = 'http://{}:{}'.format(instance['host'], instance['port'])
    for url in ('{}/servers/localhost/statistics'.format(base), '{}/api'.format(base)):
        fake_http.register_response('GET', url, outcome)


def test_metadata_unit(datadog_agent, fake_http):
    version = common._get_pdns_version()
    if version == 3:
        instance = common.CONFIG
    elif version == 4:
        instance = common.CONFIG_V4
    check = PowerDNSRecursorCheck("powerdns_recursor", {}, [instance])
    check.check_id = 'test:123'
    check.log = mock.MagicMock()

    config_obj, tags = check._get_config(instance)

    _register_metadata_outcome(fake_http, instance, HTTPClientReadTimeoutError('read timed out'))
    check._collect_metadata(config_obj)
    datadog_agent.assert_metadata_count(0)
    check.log.debug.assert_called_with('Error collecting PowerDNS Recursor version: %s', 'read timed out')

    datadog_agent.reset()
    _register_metadata_outcome(fake_http, instance, FakeHTTPResponse())
    check._collect_metadata(config_obj)
    datadog_agent.assert_metadata_count(0)
    check.log.debug.assert_called_with("Couldn't find the PowerDNS Recursor Server version header")

    datadog_agent.reset()
    _register_metadata_outcome(fake_http, instance, FakeHTTPResponse(headers={'Server': 'wrong_stuff'}))
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
