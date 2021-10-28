# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import mock
import pytest
import requests

from datadog_checks.dev.http import MockResponse
from datadog_checks.powerdns_recursor import PowerDNSRecursorCheck

from . import common


def test_metadata_unit(datadog_agent):
    version = common._get_pdns_version()
    if version == 3:
        instance = common.CONFIG
    elif version == 4:
        instance = common.CONFIG_V4
    check = PowerDNSRecursorCheck("powerdns_recursor", {}, [instance])
    check.check_id = 'test:123'
    check.log = mock.MagicMock()

    config_obj, tags = check._get_config(instance)

    with mock.patch('requests.get', side_effect=requests.exceptions.Timeout()):
        check._collect_metadata(config_obj)
        datadog_agent.assert_metadata_count(0)
        check.log.debug.assert_called_with('Error collecting PowerDNS Recursor version: %s', '')

    datadog_agent.reset()
    with mock.patch('requests.get', return_value=MockResponse()):
        check._collect_metadata(config_obj)
        datadog_agent.assert_metadata_count(0)
        check.log.debug.assert_called_with("Couldn't find the PowerDNS Recursor Server version header")

    datadog_agent.reset()
    with mock.patch('requests.get', return_value=MockResponse(headers={'Server': 'wrong_stuff'})):
        check._collect_metadata(config_obj)
        datadog_agent.assert_metadata_count(0)
        check.log.debug.assert_called_with(
            'Error while decoding PowerDNS Recursor version: %s', 'list index out of range'
        )


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
