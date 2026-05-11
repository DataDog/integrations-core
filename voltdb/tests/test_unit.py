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
            "either 'host' or 'hosts' is required",
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
        pytest.param(
            {'url': 'http://localhost:8080'},
            "'username' and 'password' are required when 'url' is set",
            id='http-mode-needs-credentials',
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
    'url, expected_netloc',
    [
        pytest.param('http://localhost:8080', ('localhost', 8080), id='http-explicit-port'),
        pytest.param('https://voltdb.example:8443', ('voltdb.example', 8443), id='https-explicit-port'),
        pytest.param('http://my-cluster', ('my-cluster', 80), id='http-default-port'),
        pytest.param('https://my-cluster', ('my-cluster', 443), id='https-default-port'),
    ],
)
def test_url_activates_http_mode(url, expected_netloc):
    """Setting `url` selects the HTTP/VMC transport. The URL's host and port are
    used directly (no port-coercion to 21212 — that's the native client port)."""
    from datadog_checks.voltdb.config import MODE_HTTP

    config = Config({'url': url, 'username': 'u', 'password': 'p'})
    assert config.mode == MODE_HTTP
    assert config.url == url
    assert config.netloc == expected_netloc


def test_host_without_url_uses_native_mode():
    """Setting `host` (without `url`) selects the native binary transport."""
    from datadog_checks.voltdb.config import MODE_NATIVE

    config = Config({'host': 'db-1.example', 'username': 'u', 'password': 'p'})
    assert config.mode == MODE_NATIVE
    assert config.netloc == ('db-1.example', 21212)
    assert config.endpoints == [('db-1.example', 21212)]


def test_hosts_list_expands_to_endpoints():
    """`hosts:` accepts either bare hostnames (using the global `port`) or
    'host:port' strings. Endpoints are tried in order."""
    config = Config(
        {
            'hosts': ['db-1.example', 'db-2.example:21222', 'db-3.example'],
            'port': 21232,
            'username': 'u',
            'password': 'p',
        }
    )
    assert config.endpoints == [
        ('db-1.example', 21232),
        ('db-2.example', 21222),
        ('db-3.example', 21232),
    ]
    # netloc points at the first endpoint for stable tag values.
    assert config.netloc == ('db-1.example', 21232)


def test_hosts_takes_precedence_over_host():
    """If both `host` and `hosts` are set, `hosts` wins so users can opt into
    failover by just adding a `hosts:` entry."""
    config = Config({'host': 'ignored.example', 'hosts': ['db-1.example', 'db-2.example']})
    assert config.endpoints == [('db-1.example', 21212), ('db-2.example', 21212)]


@pytest.mark.parametrize(
    'instance, match',
    [
        pytest.param(
            {'hosts': ['db-1.example:abc']},
            'has an invalid port',
            id='non-numeric-port',
        ),
        pytest.param(
            {'hosts': ['db-1.example:0']},
            'non-positive port',
            id='zero-port',
        ),
        pytest.param(
            {'hosts': ['']},
            'non-empty',
            id='empty-entry',
        ),
        pytest.param(
            {'hosts': 'db-1.example'},
            "'hosts' must be a list",
            id='hosts-not-a-list',
        ),
    ],
)
def test_hosts_validation_errors(instance, match):
    with pytest.raises(ConfigurationError, match=match):
        Config(instance)


def test_client_failover_tries_each_endpoint(monkeypatch):
    """When the first endpoint refuses connection, the client tries the next one."""
    from datadog_checks.voltdb.client import Client

    attempts = []

    class FakeFser:
        def close(self):
            pass

    def fake_init(host, port, **_):
        attempts.append((host, port))
        if host == 'down.example':
            raise ConnectionRefusedError('first node is down')
        return FakeFser()

    monkeypatch.setattr(Client, '_open', lambda self, host, port: fake_init(host, port))

    client = Client(
        endpoints=[('down.example', 21212), ('up.example', 21212)],
    )
    fser = client._get_connection()
    assert isinstance(fser, FakeFser)
    assert attempts == [('down.example', 21212), ('up.example', 21212)]
    assert client.active_endpoint == ('up.example', 21212)


def test_client_raises_when_no_endpoint_is_reachable(monkeypatch):
    """If every endpoint refuses connection, the client surfaces the last error."""
    from datadog_checks.voltdb.client import Client

    def always_refuse(self, host, port):
        raise ConnectionRefusedError('{}:{} is down'.format(host, port))

    monkeypatch.setattr(Client, '_open', always_refuse)

    client = Client(endpoints=[('a.example', 21212), ('b.example', 21212)])
    with pytest.raises(ConnectionRefusedError, match='b.example:21212 is down'):
        client._get_connection()
    assert client.active_endpoint is None


def test_client_requires_at_least_one_endpoint():
    from datadog_checks.voltdb.client import Client

    with pytest.raises(ValueError, match='at least one'):
        Client(endpoints=[])


def test_client_call_procedure_returns_response(monkeypatch):
    """Happy path: the client opens a connection, hands it to VoltProcedure,
    and returns the response object."""
    import mock
    import voltdbclient

    from datadog_checks.voltdb.client import Client

    fake_fser = mock.MagicMock()
    monkeypatch.setattr(Client, '_open', lambda self, host, port: fake_fser)

    fake_response = mock.MagicMock()
    fake_proc = mock.MagicMock()
    fake_proc.call.return_value = fake_response
    monkeypatch.setattr(voltdbclient, 'VoltProcedure', lambda fser, name, types: fake_proc)

    client = Client(endpoints=[('h.example', 21212)])
    resp = client.call_procedure('@Statistics', ['CPU', 0])
    assert resp is fake_response
    fake_proc.call.assert_called_once_with(['CPU', 0])


def test_client_call_procedure_retries_once_on_stale_connection(monkeypatch):
    """If a procedure call fails on an existing connection, the client closes,
    reconnects, and retries once. Verifies the second-attempt path."""
    import mock
    import voltdbclient

    from datadog_checks.voltdb.client import Client

    opens = []

    def fake_open(self, host, port):
        f = mock.MagicMock(name='fser-{}'.format(len(opens)))
        opens.append(f)
        return f

    monkeypatch.setattr(Client, '_open', fake_open)

    good_response = mock.MagicMock(name='good')
    call_count = {'n': 0}

    def fake_proc(fser, name, types):
        proc = mock.MagicMock()

        def call(params, timeout=None):
            call_count['n'] += 1
            if call_count['n'] == 1:
                # Pretend the first call (on the cached connection) fails mid-flight.
                raise BrokenPipeError('mid-flight failure')
            return good_response

        proc.call.side_effect = call
        return proc

    monkeypatch.setattr(voltdbclient, 'VoltProcedure', fake_proc)

    client = Client(endpoints=[('h.example', 21212)])
    # Prime the cached connection so the next call_procedure goes through the
    # 'had_connection = True' branch.
    client._get_connection()
    resp = client.call_procedure('@Ping')
    assert resp is good_response
    assert call_count['n'] == 2  # initial failure + retry success


def test_client_raise_for_status():
    from datadog_checks.voltdb.client import Client, VoltDBError

    client = Client(endpoints=[('h.example', 21212)])
    # Success path: should not raise.
    ok_resp = type('R', (), {'status': Client.SUCCESS, 'statusString': None})()
    client.raise_for_status(ok_resp)
    # Failure path: VoltDBError carries the status code and string.
    bad_resp = type('R', (), {'status': -2, 'statusString': 'connection lost'})()
    with pytest.raises(VoltDBError, match='connection lost') as exc:
        client.raise_for_status(bad_resp)
    assert exc.value.status == -2
    assert exc.value.status_string == 'connection lost'


def test_client_close_is_idempotent(monkeypatch):
    """close() can run safely whether or not a connection has been opened, and
    swallows exceptions from FastSerializer.close()."""
    import mock

    from datadog_checks.voltdb.client import Client

    client = Client(endpoints=[('h.example', 21212)])
    client.close()  # no-op when nothing is open
    assert client.active_endpoint is None

    bad_fser = mock.MagicMock()
    bad_fser.close.side_effect = OSError('underlying socket already dead')
    monkeypatch.setattr(Client, '_open', lambda self, host, port: bad_fser)
    client._get_connection()
    assert client.active_endpoint == ('h.example', 21212)
    client.close()  # must not propagate the OSError
    assert client.active_endpoint is None


def test_infer_volt_type_distinguishes_bool_int_float_string():
    from voltdbclient import FastSerializer

    from datadog_checks.voltdb.client import _infer_volt_type

    # bool must come before int (bool is a subclass of int in Python).
    assert _infer_volt_type(True) == FastSerializer.VOLTTYPE_TINYINT
    assert _infer_volt_type(42) == FastSerializer.VOLTTYPE_INTEGER
    assert _infer_volt_type(3.14) == FastSerializer.VOLTTYPE_FLOAT
    assert _infer_volt_type('CPU') == FastSerializer.VOLTTYPE_STRING


def test_http_client_serializes_list_params_as_json():
    """`HttpClient.call_procedure` accepts both pre-serialized parameter strings
    and Python lists; lists must be JSON-encoded the way VoltDB's HTTP/JSON
    interface expects."""
    import json

    import mock

    from datadog_checks.voltdb.http_client import HttpClient

    calls = []

    def fake_get(url, auth=None, params=None, **_):
        calls.append(params)
        resp = mock.MagicMock()
        resp.raise_for_status = lambda: None
        resp.json = lambda: {'status': 1, 'results': []}
        return resp

    client = HttpClient(url='http://vmc.example:8080', http_get=fake_get, username='u', password='p')
    client.call_procedure('@Statistics', ['CPU', 0])
    client.call_procedure('@Statistics', '[CPU, 0]')  # passthrough string
    client.call_procedure('@Ping')  # no parameters

    assert calls[0] == {'Procedure': '@Statistics', 'Parameters': json.dumps(['CPU', 0])}
    assert calls[1] == {'Procedure': '@Statistics', 'Parameters': '[CPU, 0]'}
    assert calls[2] == {'Procedure': '@Ping'}


def test_http_client_raise_for_status():
    from datadog_checks.voltdb.client import VoltDBError
    from datadog_checks.voltdb.http_client import HttpClient, HttpResponse

    client = HttpClient(url='http://vmc.example:8080', http_get=lambda *a, **k: None, username='u', password='p')
    ok = HttpResponse({'status': 1, 'results': []})
    client.raise_for_status(ok)

    bad = HttpResponse({'status': 0, 'statusstring': 'unauthorized', 'results': []})
    with pytest.raises(VoltDBError, match='unauthorized'):
        client.raise_for_status(bad)


def test_url_takes_precedence_over_host():
    """When both `url` and `host` are set, the HTTP transport is chosen — the
    URL points at the VMC endpoint and `host` is ignored."""
    from datadog_checks.voltdb.config import MODE_HTTP

    config = Config({'host': 'db-1.example', 'url': 'http://vmc.example:8080', 'username': 'u', 'password': 'p'})
    assert config.mode == MODE_HTTP
    assert config.netloc == ('vmc.example', 8080)


def test_password_hashed_only_kept_for_http():
    """`password_hashed` is forwarded to the HTTP client; the native client
    ignores it (handled at client-construction time in check.py)."""
    config = Config({'url': 'http://vmc:8080', 'username': 'u', 'password': 'abc', 'password_hashed': True})
    assert config.password_hashed is True


def test_http_mode_end_to_end(aggregator, dd_run_check):
    """When `url` is set, the check uses the HTTP transport and unwraps the
    JSON response into the same `tables[].columns[].name` / `tuples` shape the
    native code path uses."""
    import mock

    def fake_get(url, auth=None, params=None, **_):
        proc = params['Procedure']
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.raise_for_status = lambda: None
        if proc == '@SystemInformation':
            resp.json = lambda: {
                'status': 1,
                'results': [
                    {
                        'schema': [{'name': 'HOST_ID'}, {'name': 'KEY'}, {'name': 'VALUE'}],
                        'data': [[0, 'VERSION', '14.2']],
                    }
                ],
            }
        elif proc == '@Statistics' and '"CPU"' in params['Parameters']:
            resp.json = lambda: {
                'status': 1,
                'results': [
                    {
                        'schema': [
                            {'name': 'TIMESTAMP'},
                            {'name': 'HOST_ID'},
                            {'name': 'HOSTNAME'},
                            {'name': 'PERCENT_USED'},
                        ],
                        'data': [[1234567890, 7, 'host-X', 42.5]],
                    }
                ],
            }
        else:
            resp.json = lambda: {'status': 1, 'results': []}
        return resp

    instance = {
        'url': 'http://vmc.example:8080',
        'username': 'doggo',
        'password': 'doggopass',
        'statistics_components': ['CPU'],
        'tags': ['live:test'],
    }
    with mock.patch('requests.Session.get', side_effect=fake_get):
        check = VoltDBCheck('voltdb', {}, [instance])
        dd_run_check(check)

    aggregator.assert_metric(
        'voltdb.cpu.percent_used',
        value=42.5,
        tags=['host_id:7', 'voltdb_hostname:host-X', 'live:test'],
    )


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
