# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import mock
import pytest

from .common import FIXTURES_PATH
from .utils import mocked_perform_request


def test_flatten_json(check):
    check = check({})
    with open(os.path.join(FIXTURES_PATH, 'nginx_plus_in.json')) as f:
        parsed = check.parse_json(f.read())
        parsed.sort()

    with open(os.path.join(FIXTURES_PATH, 'nginx_plus_out.python')) as f:
        expected = eval(f.read())

    # Check that the parsed test data is the same as the expected output
    assert parsed == expected


def test_flatten_json_timestamp(check):
    check = check({})
    assert (
        check.parse_json(
            """
    {"timestamp": "2018-10-23T12:12:23.123212Z"}
    """
        )
        == [('nginx.timestamp', 1540296743, [], 'gauge')]
    )


def test_plus_api_v2(check, instance, aggregator):
    instance = deepcopy(instance)
    instance['use_plus_api'] = True
    instance['use_plus_api_stream'] = True
    instance['plus_api_version'] = 2
    check = check(instance)
    check._perform_request = mock.MagicMock(side_effect=mocked_perform_request)
    check.check(instance)

    total = 0
    for m in aggregator.metric_names:
        total += len(aggregator.metrics(m))
    assert total == 1180


def test_plus_api_no_stream(check, instance, aggregator):
    instance = deepcopy(instance)
    instance['use_plus_api'] = True
    instance['use_plus_api_stream'] = False
    check = check(instance)
    check._perform_request = mock.MagicMock(side_effect=mocked_perform_request)
    check.check(instance)

    total = 0
    for m in aggregator.metric_names:
        total += len(aggregator.metrics(m))
    assert total == 883


def test_plus_api_v3(check, instance, aggregator):
    instance = deepcopy(instance)
    instance['use_plus_api'] = True
    instance['use_plus_api_stream'] = True
    instance['plus_api_version'] = 3
    check = check(instance)
    check._perform_request = mock.MagicMock(side_effect=mocked_perform_request)
    check.check(instance)

    total = 0
    for m in aggregator.metric_names:
        total += len(aggregator.metrics(m))
    assert total == 1189
    aggregator.assert_metric_has_tag('nginx.stream.zone_sync.zone.records_total', 'zone:zone1', count=1)
    aggregator.assert_metric_has_tag('nginx.stream.zone_sync.zone.records_total', 'zone:zone2', count=1)


def test_nest_payload(check):
    check = check({})
    keys = ["foo", "bar"]
    payload = {"key1": "val1", "key2": "val2"}

    result = check._nest_payload(keys, payload)
    expected = {"foo": {"bar": payload}}

    assert result == expected


@pytest.mark.parametrize(
    'test_case, extra_config, expected_http_kwargs',
    [
        (
            "legacy auth config",
            {'user': 'legacy_foo', 'password': 'legacy_bar'},
            {'auth': ('legacy_foo', 'legacy_bar')},
        ),
        ("new auth config", {'username': 'new_foo', 'password': 'new_bar'}, {'auth': ('new_foo', 'new_bar')}),
        ("legacy ssl config True", {'ssl_validation': True}, {'verify': True}),
        ("legacy ssl config False", {'ssl_validation': False}, {'verify': False}),
    ],
)
def test_config(check, instance, test_case, extra_config, expected_http_kwargs):
    instance = deepcopy(instance)
    instance.update(extra_config)

    c = check(instance)

    with mock.patch('datadog_checks.base.utils.http.requests') as r:
        r.get.return_value = mock.MagicMock(status_code=200, content=b'{}')

        c.check(instance)

        http_wargs = dict(
            auth=mock.ANY, cert=mock.ANY, headers=mock.ANY, proxies=mock.ANY, timeout=mock.ANY, verify=mock.ANY
        )
        http_wargs.update(expected_http_kwargs)

        r.get.assert_called_with('http://localhost:8080/nginx_status', **http_wargs)


def test_no_version(check, instance, caplog):
    c = check(instance)

    with mock.patch('datadog_checks.base.utils.http.requests') as r:
        r.get.return_value = mock.MagicMock(status_code=200, content=b'{}', headers={'server': 'nginx'})

        c.check(instance)

    errors = [record for record in caplog.records if record.levelname == "ERROR"]
    assert not errors
