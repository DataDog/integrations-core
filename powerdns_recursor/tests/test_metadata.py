# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import mock
import pytest

from datadog_checks.base.stubs.http import FakeHTTPResponse
from datadog_checks.base.utils.http_exceptions import HTTPClientTimeoutError
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


def test_metadata_unit_timeout(datadog_agent, fake_http):
    check, config_obj = _make_check()
    legacy_url = "http://{}:{}/servers/localhost/statistics".format(config_obj.host, config_obj.port)
    v4_url = "http://{}:{}/api".format(config_obj.host, config_obj.port)
    urls = [v4_url] if config_obj.version == 4 else [legacy_url, v4_url]
    for url in urls:
        fake_http.register_response('GET', url, HTTPClientTimeoutError(''))

    check._collect_metadata(config_obj)

    datadog_agent.assert_metadata_count(0)
    check.log.debug.assert_called_with('Error collecting PowerDNS Recursor version: %s', '')
    fake_http.assert_all_responses_consumed()


def test_metadata_unit_missing_header(datadog_agent, fake_http):
    check, config_obj = _make_check()
    url = (
        "http://{}:{}/api".format(config_obj.host, config_obj.port)
        if config_obj.version == 4
        else "http://{}:{}/servers/localhost/statistics".format(config_obj.host, config_obj.port)
    )
    fake_http.register_response('GET', url, FakeHTTPResponse(headers={}))

    check._collect_metadata(config_obj)

    datadog_agent.assert_metadata_count(0)
    check.log.debug.assert_called_with("Couldn't find the PowerDNS Recursor Server version header")
    fake_http.assert_all_responses_consumed()


def test_metadata_unit_bad_version_header(datadog_agent, fake_http):
    check, config_obj = _make_check()
    url = (
        "http://{}:{}/api".format(config_obj.host, config_obj.port)
        if config_obj.version == 4
        else "http://{}:{}/servers/localhost/statistics".format(config_obj.host, config_obj.port)
    )
    fake_http.register_response('GET', url, FakeHTTPResponse(headers={'Server': 'wrong_stuff'}))

    check._collect_metadata(config_obj)

    datadog_agent.assert_metadata_count(0)
    check.log.debug.assert_called_with('Error while decoding PowerDNS Recursor version: %s', 'list index out of range')
    fake_http.assert_all_responses_consumed()


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
