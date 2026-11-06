# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import threading
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


def test_client_requires_at_least_one_endpoint():
    from datadog_checks.voltdb.client import Client

    with pytest.raises(ValueError, match='at least one'):
        Client(endpoints=[])


def test_client_constructs_volt_client_with_all_seeds(monkeypatch):
    """The Client passes every endpoint as a seed to the topology-aware
    VoltClient (which then discovers the rest of the cluster and opens one
    connection per node)."""
    import mock

    from datadog_checks.voltdb import client as client_mod
    from datadog_checks.voltdb.client import Client

    made = {}

    def fake_volt_client(**kwargs):
        made.update(kwargs)
        return mock.MagicMock()

    monkeypatch.setattr(client_mod, 'VoltClient', fake_volt_client)

    Client(
        endpoints=[('db-1.example', 21212), ('db-2.example', 21212), ('db-3.example', 21212)],
        username='doggo',
        password='doggopass',
    )._get_client()

    assert made['hosts'] == ['db-1.example', 'db-2.example', 'db-3.example']
    assert made['port'] == 21212
    assert made['username'] == 'doggo'
    assert made['password'] == 'doggopass'


def test_client_warns_on_mixed_ports():
    """The topology-aware client uses one shared port for every seed. If
    endpoints declare different ports, we take the first one and warn."""
    import logging

    from datadog_checks.voltdb.client import Client

    log = logging.getLogger('test-mixed-ports')
    warnings = []
    log.warning = lambda *args: warnings.append(args)  # type: ignore[method-assign]

    client = Client(
        endpoints=[('db-1.example', 21212), ('db-2.example', 31212)],
        log=log,
    )
    assert client._port == 21212
    assert client._hosts == ['db-1.example', 'db-2.example']
    assert len(warnings) == 1
    assert warnings[0][1:] == ([21212, 31212], 21212)


@pytest.mark.parametrize(
    'procedure_timeout, expected',
    [
        pytest.param(30, 30, id='explicit'),
        pytest.param(None, threading.TIMEOUT_MAX, id='disabled'),
    ],
)
def test_client_procedure_timeout(monkeypatch, procedure_timeout, expected):
    """VoltClient puts a deadline on every call, so a disabled timeout maps to
    the largest wait threading accepts rather than None."""
    import mock

    from datadog_checks.voltdb import client as client_mod
    from datadog_checks.voltdb.client import Client

    made = {}
    monkeypatch.setattr(client_mod, 'VoltClient', lambda **kw: made.update(kw) or mock.MagicMock())

    Client(endpoints=[('h.example', 21212)], procedure_timeout=procedure_timeout)._get_client()
    assert made['procedure_timeout'] == expected


def test_client_call_procedure_delegates_and_infers_types(monkeypatch):
    """call_procedure infers a VoltType per parameter, sends through
    VoltClient.call_async, and returns the response unchanged."""
    import mock
    import voltdbclient

    from datadog_checks.voltdb import client as client_mod
    from datadog_checks.voltdb.client import Client

    fake_response = mock.MagicMock()
    fake_volt = mock.MagicMock()
    fake_volt.call_async.return_value = common.completed_future(lambda: fake_response)
    monkeypatch.setattr(client_mod, 'VoltClient', lambda **_: fake_volt)

    client = Client(endpoints=[('h.example', 21212)])
    resp = client.call_procedure('@Statistics', ['CPU', 0])

    assert resp is fake_response
    fake_volt.call_async.assert_called_once_with(
        '@Statistics',
        [voltdbclient.FastSerializer.VOLTTYPE_STRING, voltdbclient.FastSerializer.VOLTTYPE_INTEGER],
        ['CPU', 0],
    )


def _lost_call():
    from voltclient import VoltConnectionError

    raise VoltConnectionError('connection to db-2 lost')


def test_client_resends_once_when_call_loses_its_connection(monkeypatch):
    """A call whose connection dies while it is in flight is sent once more on the
    same pool, which has already healed onto the remaining nodes."""
    import mock

    from datadog_checks.voltdb import client as client_mod
    from datadog_checks.voltdb.client import Client

    good = mock.MagicMock(status=1)
    fake_volt = mock.MagicMock()
    fake_volt.call_async.side_effect = [common.completed_future(_lost_call), common.completed_future(lambda: good)]
    monkeypatch.setattr(client_mod, 'VoltClient', lambda **_: fake_volt)

    client = Client(endpoints=[('h.example', 21212)])
    assert client.call_procedure('@SystemInformation', ['OVERVIEW']) is good
    assert fake_volt.call_async.call_count == 2
    fake_volt.close.assert_not_called()


def test_client_resends_only_once(monkeypatch):
    """If the resend is lost too, the error surfaces; the pool is kept, since it
    keeps healing in the background."""
    import mock
    from voltclient import VoltConnectionError

    from datadog_checks.voltdb import client as client_mod
    from datadog_checks.voltdb.client import Client

    fake_volt = mock.MagicMock()
    fake_volt.call_async.side_effect = lambda *a: common.completed_future(_lost_call)
    monkeypatch.setattr(client_mod, 'VoltClient', lambda **_: fake_volt)

    client = Client(endpoints=[('h.example', 21212)])
    with pytest.raises(VoltConnectionError, match='db-2 lost'):
        client.call_procedure('@Ping')
    assert fake_volt.call_async.call_count == 2
    assert client._client is fake_volt


def test_client_does_not_resend_on_timeout(monkeypatch):
    """A timeout means a slow cluster, not a lost connection: resending would only
    double the wait."""
    import mock
    from voltclient import VoltTimeoutError

    from datadog_checks.voltdb import client as client_mod
    from datadog_checks.voltdb.client import Client

    def timed_out():
        raise VoltTimeoutError('no response within 60s')

    fake_volt = mock.MagicMock()
    fake_volt.call_async.return_value = common.completed_future(timed_out)
    monkeypatch.setattr(client_mod, 'VoltClient', lambda **_: fake_volt)

    client = Client(endpoints=[('h.example', 21212)])
    with pytest.raises(VoltTimeoutError):
        client.call_procedure('@Ping')
    assert fake_volt.call_async.call_count == 1


def test_client_rebuilds_pool_from_seeds_when_no_connections(monkeypatch):
    """When every pooled connection is gone, the pool is rebuilt from the configured
    seeds (whose addresses may have changed) and the call is sent once more."""
    import mock
    from voltclient import VoltNoConnectionsError

    from datadog_checks.voltdb import client as client_mod
    from datadog_checks.voltdb.client import Client

    good = mock.MagicMock(status=1)
    stale = mock.MagicMock()
    stale.call_async.side_effect = VoltNoConnectionsError('all nodes down')
    fresh = mock.MagicMock()
    fresh.call_async.return_value = common.completed_future(lambda: good)
    pools = iter([stale, fresh])
    monkeypatch.setattr(client_mod, 'VoltClient', lambda **_: next(pools))

    client = Client(endpoints=[('h.example', 21212)])
    client._get_client()
    assert client.call_procedure('@Ping') is good
    stale.close.assert_called_once()
    assert client._client is fresh


def test_client_does_not_rebuild_a_pool_it_just_built(monkeypatch):
    """A pool built for this very call that already has no connections is not
    rebuilt again: one pass over the seeds per call."""
    import mock
    from voltclient import VoltNoConnectionsError

    from datadog_checks.voltdb import client as client_mod
    from datadog_checks.voltdb.client import Client

    constructions = []
    fake_volt = mock.MagicMock()
    fake_volt.call_async.side_effect = VoltNoConnectionsError('all nodes down')
    monkeypatch.setattr(client_mod, 'VoltClient', lambda **_: constructions.append(1) or fake_volt)

    client = Client(endpoints=[('h.example', 21212)])
    with pytest.raises(VoltNoConnectionsError):
        client.call_procedure('@Ping')
    assert len(constructions) == 1
    assert client._client is None


def test_client_waits_for_next_run_when_cluster_not_started(monkeypatch):
    """If no seed answers yet, the call fails after one pass over the seeds, and the
    next check run connects from scratch once the cluster is up."""
    import mock
    from voltclient import VoltConnectionError

    from datadog_checks.voltdb import client as client_mod
    from datadog_checks.voltdb.client import Client

    good = mock.MagicMock(status=1)
    started = mock.MagicMock()
    started.call_async.return_value = common.completed_future(lambda: good)
    constructions = []

    def volt_client(**_):
        constructions.append(1)
        if len(constructions) == 1:
            raise VoltConnectionError('could not connect to any of the seed hosts')
        return started

    monkeypatch.setattr(client_mod, 'VoltClient', volt_client)

    client = Client(endpoints=[('h.example', 21212)])
    with pytest.raises(VoltConnectionError, match='seed hosts'):
        client.call_procedure('@Ping')
    assert len(constructions) == 1
    assert client._client is None

    assert client.call_procedure('@Ping') is good
    assert len(constructions) == 2


def test_client_raise_for_status():
    from datadog_checks.voltdb.client import Client, VoltDBError

    client = Client(endpoints=[('h.example', 21212)])
    ok_resp = type('R', (), {'status': Client.SUCCESS, 'statusString': None})()
    client.raise_for_status(ok_resp)

    bad_resp = type('R', (), {'status': -2, 'statusString': 'connection lost'})()
    with pytest.raises(VoltDBError, match='connection lost') as exc:
        client.raise_for_status(bad_resp)
    assert exc.value.status == -2
    assert exc.value.status_string == 'connection lost'


def test_client_close_is_idempotent(monkeypatch):
    """close() can run safely whether or not a VoltClient has been opened, and
    swallows exceptions from VoltClient.close()."""
    import mock

    from datadog_checks.voltdb import client as client_mod
    from datadog_checks.voltdb.client import Client

    client = Client(endpoints=[('h.example', 21212)])
    client.close()  # no-op when nothing is open
    assert client._client is None

    bad_volt = mock.MagicMock()
    bad_volt.close.side_effect = OSError('background thread already dead')
    monkeypatch.setattr(client_mod, 'VoltClient', lambda **_: bad_volt)
    client._get_client()
    client.close()  # must not propagate the OSError
    assert client._client is None


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
    """When `url` is set, the check uses the HTTP transport and exposes
    responses through the same `tables[].columns[].name` / `tuples` shape
    the native code path uses."""
    import mock

    from datadog_checks.voltdb.http_client import HttpResponse

    def fake_call_procedure(procedure, params=None):
        if procedure == '@SystemInformation':
            return HttpResponse(
                {
                    'status': 1,
                    'results': [
                        {
                            'schema': [{'name': 'HOST_ID'}, {'name': 'KEY'}, {'name': 'VALUE'}],
                            'data': [[0, 'VERSION', '14.2']],
                        }
                    ],
                }
            )
        if procedure == '@Statistics' and params and params[0] == 'CPU':
            return HttpResponse(
                {
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
            )
        return HttpResponse({'status': 1, 'results': []})

    instance = {
        'url': 'http://vmc.example:8080',
        'username': 'doggo',
        'password': 'doggopass',
        'statistics_components': ['CPU'],
        'tags': ['live:test'],
    }
    with mock.patch('datadog_checks.voltdb.check.HttpClient') as m:
        client = m.return_value
        client.SUCCESS = HttpResponse.SUCCESS
        client.call_procedure.side_effect = fake_call_procedure
        client.raise_for_status = lambda r: None
        client.close = lambda: None

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
        client.call_procedure_async = lambda procedure, params=None: common.completed_future(
            fake_call, procedure, params
        )
        client.result = lambda future, procedure, params=None: future.result()
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


class RecordingClient(object):
    """Stands in for the native Client, logging each send and each wait so tests
    can tell whether calls overlapped."""

    SUCCESS = 1

    def __init__(self, fail_send=None, fail_send_for=None):
        self.events = []
        self.send_attempts = 0
        self._fail_send = fail_send
        self._fail_send_for = fail_send_for or {}

    def _respond(self, procedure, params):
        import mock

        table = mock.MagicMock()
        table.columns = []
        table.tuples = []
        response = mock.MagicMock(status=1, statusString=None, tables=[table])
        if procedure == '@SystemInformation':
            key, value = mock.MagicMock(), mock.MagicMock()
            key.name, value.name = 'KEY', 'VALUE'
            table.columns = [key, value]
            table.tuples = [('VERSION', '16.0')]
        return response

    def call_procedure_async(self, procedure, params=None):
        self.send_attempts += 1
        if self._fail_send is not None:
            raise self._fail_send
        if procedure in self._fail_send_for:
            raise self._fail_send_for[procedure]
        self.events.append(('send', procedure, tuple(params or ())))
        events = self.events
        response = self._respond(procedure, params)

        class _Future(object):
            def result(self):
                events.append(('wait', procedure, tuple(params or ())))
                return response

        return _Future()

    def call_procedure(self, procedure, params=None):
        self.events.append(('sync', procedure, tuple(params or ())))
        if self._fail_send is not None:
            raise self._fail_send
        return self._respond(procedure, params)

    def result(self, future, procedure, params=None):
        return future.result()

    def raise_for_status(self, response):
        pass

    def close(self):
        pass


def _native_check(client, **instance):
    instance.setdefault('host', 'localhost')
    instance.setdefault('statistics_components', ['CPU', 'MEMORY', 'GC'])
    check = VoltDBCheck('voltdb', {}, [instance])
    check._client = client
    return check


def test_native_calls_are_all_sent_before_any_is_awaited(dd_run_check):
    """Every call of a run is on the wire before the check waits on the first
    response, so round-trips overlap instead of adding up."""
    client = RecordingClient()
    dd_run_check(_native_check(client))

    kinds = [kind for kind, _, _ in client.events]
    assert 'sync' not in kinds
    assert kinds == ['send'] * 4 + ['wait'] * 4
    assert [(p, a) for _, p, a in client.events[:4]] == [
        ('@SystemInformation', ('OVERVIEW',)),
        ('@Statistics', ('CPU',)),
        ('@Statistics', ('MEMORY',)),
        ('@Statistics', ('GC', 1)),
    ]


def test_interval_gated_custom_query_runs_synchronously(dd_run_check):
    """A custom query with its own collection_interval is not sent ahead of
    time: QueryManager alone decides when it is due."""
    client = RecordingClient()
    check = _native_check(
        client,
        statistics_components=['CPU'],
        custom_queries=[
            {'query': 'HeroStats', 'columns': [{'name': 'custom.heroes', 'type': 'gauge'}], 'collection_interval': 60},
        ],
    )
    dd_run_check(check)

    assert ('sync', 'HeroStats', ()) in client.events
    assert ('send', 'HeroStats', ()) not in client.events


def test_duplicate_query_is_sent_once_ahead_then_synchronously(dd_run_check):
    """A custom query identical to a built-in one is sent ahead only once; the
    second consumer makes its own call instead of reusing a spent response."""
    client = RecordingClient()
    check = _native_check(
        client,
        statistics_components=['CPU'],
        custom_queries=[
            {'query': '@Statistics:[CPU]', 'columns': [{'name': 'custom.cpu', 'type': 'gauge'}]},
        ],
    )
    dd_run_check(check)

    assert client.events.count(('send', '@Statistics', ('CPU',))) == 1
    assert client.events.count(('sync', '@Statistics', ('CPU',))) == 1


def test_unreachable_cluster_costs_one_connection_attempt_per_run(aggregator, dd_run_check):
    """With the cluster down (e.g. not started yet), a run makes a single pass over
    the seeds and reports it on the service check; no call retries on its own."""
    from voltclient import VoltConnectionError

    client = RecordingClient(fail_send=VoltConnectionError('could not connect to any of the seed hosts'))
    check = _native_check(client)

    with pytest.raises(Exception, match='seed hosts'):
        dd_run_check(check)
    aggregator.assert_service_check('voltdb.can_connect', VoltDBCheck.CRITICAL)
    assert client.send_attempts == 1
    assert not [e for e in client.events if e[0] == 'sync']
    assert check._inflight == {}
    assert check._send_error is None


def test_send_error_for_one_call_affects_only_that_call(aggregator, dd_run_check):
    """A call that can't be sent for a reason other than connectivity (e.g. a custom
    query parameter that can't be serialized) is retried on its own; the rest of the
    run is unaffected."""
    client = RecordingClient(fail_send_for={'HeroStats': ValueError('value out of range')})
    check = _native_check(
        client,
        statistics_components=['CPU'],
        custom_queries=[{'query': 'HeroStats', 'columns': [{'name': 'custom.heroes', 'type': 'gauge'}]}],
    )
    dd_run_check(check)

    aggregator.assert_service_check('voltdb.can_connect', VoltDBCheck.OK)
    assert ('send', '@Statistics', ('CPU',)) in client.events
    assert ('sync', 'HeroStats', ()) in client.events


def test_check_before_queries_compile_still_reports_connection(aggregator):
    """check() called directly, before run() has compiled the queries, still
    reaches the version call and reports the connection failure."""
    from voltclient import VoltConnectionError

    client = RecordingClient(fail_send=VoltConnectionError('refused'))
    check = _native_check(client)

    with pytest.raises(VoltConnectionError):
        check.check({})
    aggregator.assert_service_check('voltdb.can_connect', VoltDBCheck.CRITICAL)


def test_http_mode_does_not_send_ahead():
    """The HTTP transport keeps its sequential behavior."""
    check = VoltDBCheck('voltdb', {}, [{'url': 'http://vmc.example:8080', 'username': 'u', 'password': 'p'}])
    check._client = RecordingClient()
    assert check._submit_calls() == ({}, None)


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
