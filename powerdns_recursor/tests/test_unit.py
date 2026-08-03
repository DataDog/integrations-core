# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from copy import deepcopy

import pytest

from datadog_checks.powerdns_recursor import PowerDNSRecursorCheck

from . import common

pytestmark = pytest.mark.unit


def test_bad_config(aggregator):
    check = PowerDNSRecursorCheck("powerdns_recursor", {}, [common.BAD_CONFIG])
    with pytest.raises(Exception):
        check.check(common.BAD_CONFIG)

    service_check_tags = common._config_sc_tags(common.BAD_CONFIG)
    aggregator.assert_service_check('powerdns.recursor.can_connect', status=check.CRITICAL, tags=service_check_tags)
    assert len(aggregator._metrics) == 0


def test_very_bad_config(aggregator):
    for config in [{}, {"host": "localhost"}, {"port": 1000}, {"host": "localhost", "port": 1000}]:
        check = PowerDNSRecursorCheck("powerdns_recursor", {}, [config])
        with pytest.raises(Exception):
            check.check(config)

    assert len(aggregator._metrics) == 0


def test_api_key_headers():
    instance = deepcopy(common.CONFIG)
    instance.update({'api_key': 'API_KEY', 'headers': {'foo': 'bar'}})
    expected_headers = {'X-API-Key': 'API_KEY', 'foo': 'bar'}

    check = PowerDNSRecursorCheck('powerdns_recursor', {}, instances=[instance])
    assert expected_headers == check._http.options['headers']
