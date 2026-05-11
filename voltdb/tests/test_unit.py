# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from typing import Optional  # noqa: F401

import pytest
from datadog_checks.base import ConfigurationError
from datadog_checks.dev.utils import get_metadata_metrics

from datadog_checks.voltdb.check import VoltDBCheck, _parse_query
from datadog_checks.voltdb.config import Config
from datadog_checks.voltdb.types import Instance  # noqa: F401

from . import common


@pytest.mark.parametrize(
    'instance, match',
    [
        pytest.param(
            {'username': 'doggo', 'password': 'doggopass'},
            'host is required',
            id='host-missing',
        ),
        pytest.param(
            {
                'host': 'localhost',
                'port': 0,
                'username': 'doggo',
                'password': 'doggopass',
            },
            'port must be a positive integer',
            id='port-invalid',
        ),
    ],
)
def test_config_errors(instance, match):
    # type: (Instance, str) -> None
    with pytest.raises(ConfigurationError, match=match):
        Config(instance)


@pytest.mark.parametrize(
    'instance, tags',
    [
        pytest.param(None, [], id='none'),
        pytest.param(['test:example'], ['test:example'], id='some'),
    ],
)
def test_custom_tags(instance, tags):
    # type: (Instance, Optional[list]) -> None
    instance = {'host': 'localhost', 'username': 'doggo', 'password': 'doggopass'}
    if tags is not None:
        instance['tags'] = tags
    config = Config(instance)
    assert config.tags == tags


def test_default_port():
    # type: () -> None
    config = Config({'host': 'localhost', 'username': 'doggo', 'password': 'doggopass'})
    assert config.netloc == ('localhost', 21212)


def test_custom_port():
    # type: () -> None
    config = Config(
        {
            'host': 'localhost',
            'port': 31212,
            'username': 'doggo',
            'password': 'doggopass',
        }
    )
    assert config.netloc == ('localhost', 31212)


def test_no_credentials():
    # type: () -> None
    # Native client allows empty credentials when the cluster does not require auth.
    config = Config({'host': 'localhost'})
    assert config.username == ''
    assert config.password == ''


@pytest.mark.parametrize(
    'instance, expected',
    [
        pytest.param({'host': 'localhost'}, 60, id='default'),
        pytest.param({'host': 'localhost', 'procedure_timeout': 30}, 30, id='explicit'),
        pytest.param({'host': 'localhost', 'procedure_timeout': 0}, None, id='zero-disables'),
        pytest.param({'host': 'localhost', 'procedure_timeout': -1}, None, id='negative-disables'),
    ],
)
def test_procedure_timeout_default(instance, expected):
    """procedure_timeout defaults to 60s so a hung VoltDB procedure can't block
    the check forever. Setting it to 0 (or any non-positive number) restores
    the 'wait indefinitely' behavior."""
    config = Config(instance)
    assert config.procedure_timeout == expected


@pytest.mark.parametrize(
    'url, expected_host, expected_use_ssl',
    [
        pytest.param('http://localhost:8080', 'localhost', False, id='http'),
        pytest.param('https://voltdb.example:8443', 'voltdb.example', True, id='https'),
        pytest.param('http://my-cluster', 'my-cluster', False, id='no-port'),
    ],
)
def test_url_backwards_compat(url, expected_host, expected_use_ssl):
    """The legacy `url` option keeps working: host is parsed from the URL,
    `https` flips on `use_ssl`, and the port defaults to the native client port."""
    warnings = []
    config = Config(
        {'url': url, 'username': 'u', 'password': 'p'},
        warning=lambda *args: warnings.append(args),
    )
    assert config.host == expected_host
    assert config.port == 21212
    assert config.use_ssl is expected_use_ssl
    assert warnings, 'expected a deprecation warning when `url` is used'


def test_url_does_not_override_explicit_host():
    """If both `host` and `url` are set, `host` wins."""
    config = Config({'host': 'explicit-host', 'url': 'http://other-host:8080'})
    assert config.host == 'explicit-host'
    assert config.port == 21212


@pytest.mark.parametrize(
    'query, expected_procedure, expected_params',
    [
        pytest.param(
            '@SystemInformation:[OVERVIEW]',
            '@SystemInformation',
            ['OVERVIEW'],
            id='single-string',
        ),
        pytest.param('@Statistics:[CPU]', '@Statistics', ['CPU'], id='one-string'),
        pytest.param(
            '@Statistics:[COMMANDLOG, 1]',
            '@Statistics',
            ['COMMANDLOG', 1],
            id='string-and-int',
        ),
        pytest.param('HeroStats', 'HeroStats', [], id='no-params'),
        pytest.param('Proc:[]', 'Proc', [], id='empty-list'),
    ],
)
def test_parse_query(query, expected_procedure, expected_params):
    procedure, params = _parse_query(query)
    assert procedure == expected_procedure
    assert params == expected_params


def test_columns_resolved_by_name(aggregator, dd_run_check):
    """The check looks up columns by name, so the server can return extra columns
    in any order without breaking the integration."""
    import mock

    def _make_table(headers, rows):
        table = mock.MagicMock()
        table.tuples = rows
        cols = []
        for n in headers:
            c = mock.MagicMock()
            c.name = n
            cols.append(c)
        table.columns = cols
        return table

    def _make_response(table):
        r = mock.MagicMock()
        r.status = 1
        r.statusString = None
        r.tables = [table]
        return r

    def fake_call(procedure, params=None):
        params = params or []
        if procedure == '@SystemInformation':
            return _make_response(_make_table(['HOST_ID', 'KEY', 'VALUE'], [(0, 'VERSION', '14.2')]))
        # @Statistics CPU response with columns shuffled and an extra trailing column.
        if procedure == '@Statistics' and params and params[0] == 'CPU':
            headers = [
                'EXTRA_NEW_COL',
                'PERCENT_USED',
                'TIMESTAMP',
                'HOSTNAME',
                'HOST_ID',
            ]
            rows = [(999, 42.5, 1234567890, 'voltdb-host-X', 7)]
            return _make_response(_make_table(headers, rows))
        # Other statistics: missing entirely.
        return _make_response(_make_table([], []))

    with mock.patch('datadog_checks.voltdb.check.Client') as m:
        client = m.return_value
        client.SUCCESS = 1
        client.call_procedure = fake_call
        client.raise_for_status = lambda r: None
        client.close = lambda: None

        instance = {
            'host': 'localhost',
            'port': 21212,
            'statistics_components': ['CPU'],
            'tags': ['live:test'],
        }
        check = VoltDBCheck('voltdb', {}, [instance])
        dd_run_check(check)

    aggregator.assert_metric(
        'voltdb.cpu.percent_used',
        value=42.5,
        tags=['host_id:7', 'voltdb_hostname:voltdb-host-X', 'live:test'],
    )


def test_metrics_with_fixtures(mock_results, aggregator, dd_run_check, instance_all):
    check = VoltDBCheck('voltdb', {}, [instance_all])
    dd_run_check(check)

    with open(os.path.join(common.HERE, 'fixtures', 'expected_metrics.json'), 'r') as f:
        metrics = json.load(f)

    for m in metrics:
        aggregator.assert_metric(m['name'], tags=m['tags'], metric_type=m['type'])

        # Ensure we're mapping the response correctly
    aggregator.assert_metric('voltdb.memory.tuple_count', value=2847267.0)
    aggregator.assert_metric('voltdb.memory.java.max_heap', value=531998.0)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
