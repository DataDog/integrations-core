# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from datadog_checks.postgres.remote_query import (
    StaticPostgresCheckRegistry,
    execute_remote_query,
    normalize_target,
)


class FakePool:
    def __init__(self, rows=None, description=None, closed=False):
        self.rows = rows or [(1,)]
        self.description = description or [SimpleNamespace(name='value')]
        self.closed = closed
        self.requested_dbnames = []

    def is_closed(self):
        return self.closed

    @contextmanager
    def get_connection(self, dbname):
        self.requested_dbnames.append(dbname)
        yield FakeConnection(self.rows, self.description)


class FakeConnection:
    def __init__(self, rows, description):
        self.rows = rows
        self.description = description

    @contextmanager
    def cursor(self):
        yield FakeCursor(self.rows, self.description)


class FakeCursor:
    def __init__(self, rows, description):
        self.rows = rows
        self.description = description
        self.executed = None

    def execute(self, query):
        self.executed = query

    def fetchmany(self, size):
        return self.rows[:size]


def make_check(host='localhost', port=5432, dbname='datadog_test', pool=None, **metadata):
    check = SimpleNamespace(
        _config=SimpleNamespace(host=host, port=port, dbname=dbname, **metadata),
        db_pool=pool or FakePool(),
    )
    check.execute_query_raw = pytest.fail
    check._run_query_scope = pytest.fail
    check.data_observability = SimpleNamespace(run_job=pytest.fail)
    return check


def valid_request(host='LOCALHOST.', port=5432, dbname='datadog_test', **extra):
    request = {
        'target': {'host': host, 'port': port, 'dbname': dbname},
        'query': 'SELECT 1 AS value',
        'limits': {'maxRows': 10, 'maxBytes': 1048576, 'timeoutMs': 5000},
    }
    request.update(extra)
    return request


class ExplodingRegistry:
    def iter_postgres_checks(self):
        pytest.fail('registry must not be iterated')


def response_code(response):
    return response['error']['code']


def test_normalize_target_trims_lowercases_host_and_removes_one_trailing_dot():
    target = normalize_target({'host': ' Example.INTERNAL. ', 'port': 5432, 'dbname': 'postgres'})

    assert target.host == 'example.internal'
    assert target.port == 5432
    assert target.dbname == 'postgres'


def test_normalize_target_defaults_missing_port_to_5432():
    target = normalize_target({'host': 'localhost', 'dbname': 'postgres'})

    assert target.port == 5432


@pytest.mark.parametrize('port', [True, '5432', 'abc', '0', 0, -1, 65536, None])
def test_normalize_target_rejects_invalid_port_values(port):
    with pytest.raises(ValueError):
        normalize_target({'host': 'localhost', 'port': port, 'dbname': 'postgres'})


@pytest.mark.parametrize(
    'target',
    [
        {'host': '', 'port': 5432, 'dbname': 'postgres'},
        {'host': '  ', 'port': 5432, 'dbname': 'postgres'},
        {'host': 'localhost', 'port': 5432, 'dbname': ''},
        {'host': 'localhost', 'port': 5432, 'dbname': ' postgres '},
    ],
)
def test_normalize_target_rejects_empty_host_or_dbname(target):
    with pytest.raises(ValueError):
        normalize_target(target)


@pytest.mark.parametrize('field', ['extra', 'password'])
def test_rejects_unknown_request_fields_before_resolution(caplog, field):
    request = valid_request(**{field: 'SECRET_DO_NOT_LOG'})

    response = execute_remote_query(request, ExplodingRegistry())

    assert response['status'] == 'FAILED'
    assert response_code(response) == 'invalid_request'
    assert field in response['error']['message']
    assert 'SECRET_DO_NOT_LOG' not in str(response)
    assert 'SECRET_DO_NOT_LOG' not in caplog.text


def test_rejects_unknown_target_fields_before_resolution():
    request = valid_request()
    request['target']['password'] = 'SECRET_DO_NOT_LOG'

    response = execute_remote_query(request, ExplodingRegistry())

    assert response['status'] == 'FAILED'
    assert response_code(response) == 'invalid_request'
    assert 'password' in response['error']['message']
    assert 'SECRET_DO_NOT_LOG' not in str(response)


def test_rejects_unknown_limits_fields_before_resolution():
    request = valid_request()
    request['limits']['password'] = 'SECRET_DO_NOT_LOG'

    response = execute_remote_query(request, ExplodingRegistry())

    assert response['status'] == 'FAILED'
    assert response_code(response) == 'invalid_request'
    assert 'password' in response['error']['message']
    assert 'SECRET_DO_NOT_LOG' not in str(response)


@pytest.mark.parametrize('field', ['maxRows', 'maxBytes', 'timeoutMs'])
def test_rejects_string_limit_values_before_resolution(field):
    request = valid_request()
    request['limits'][field] = '10'

    response = execute_remote_query(request, ExplodingRegistry())

    assert response['status'] == 'FAILED'
    assert response_code(response) == 'invalid_request'
    assert field in response['error']['message']


def test_resolve_matches_exact_host_port_dbname_from_check_config():
    pool = FakePool()
    check = make_check(host='localhost', port=5432, dbname='datadog_test', pool=pool)

    response = execute_remote_query(valid_request(host='LOCALHOST.', port=5432), StaticPostgresCheckRegistry([check]))

    assert response['status'] == 'SUCCEEDED'
    assert response['rows'] == [{'value': 1}]
    assert pool.requested_dbnames == ['datadog_test']


def test_resolve_requires_dbname_match_even_when_host_and_port_match():
    pool = FakePool()
    check = make_check(host='localhost', port=5432, dbname='datadog_test', pool=pool)

    response = execute_remote_query(valid_request(dbname='postgres'), StaticPostgresCheckRegistry([check]))

    assert response['status'] == 'FAILED'
    assert response_code(response) == 'target_not_found'
    assert pool.requested_dbnames == []


def test_resolve_ignores_metadata_identity_matches():
    pool = FakePool()
    check = make_check(
        host='configured.internal',
        port=5432,
        dbname='datadog_test',
        pool=pool,
        reported_hostname='reported.internal',
        database_identifier='reported.internal',
    )

    response = execute_remote_query(valid_request(host='reported.internal'), StaticPostgresCheckRegistry([check]))

    assert response['status'] == 'FAILED'
    assert response_code(response) == 'target_not_found'
    assert pool.requested_dbnames == []


def test_resolve_fails_ambiguous_duplicate_configs():
    first_pool = FakePool()
    second_pool = FakePool()
    checks = [make_check(pool=first_pool), make_check(pool=second_pool)]

    response = execute_remote_query(valid_request(), StaticPostgresCheckRegistry(checks))

    assert response['status'] == 'FAILED'
    assert response_code(response) == 'target_ambiguous'
    assert first_pool.requested_dbnames == []
    assert second_pool.requested_dbnames == []


def test_execute_sets_truncated_when_more_than_max_rows_returned():
    pool = FakePool(rows=[(1,), (2,)])
    check = make_check(pool=pool)
    request = valid_request()
    request['limits']['maxRows'] = 1

    response = execute_remote_query(request, StaticPostgresCheckRegistry([check]))

    assert response['status'] == 'SUCCEEDED'
    assert response['rows'] == [{'value': 1}]
    assert response['truncated'] is True
    assert response['stats']['rowCount'] == 1


def test_execute_closed_pool_returns_target_unavailable_without_recreating_credentials():
    pool = FakePool(closed=True)
    check = make_check(pool=pool)

    response = execute_remote_query(valid_request(), StaticPostgresCheckRegistry([check]))

    assert response['status'] == 'FAILED'
    assert response_code(response) == 'target_unavailable'
    assert pool.requested_dbnames == []


@pytest.mark.parametrize('query', ['SELECT current_database()', 'SELECT 1 AS value;', ' SELECT 1 AS value'])
def test_execute_rejects_non_canonical_query_before_pool_access(query):
    pool = FakePool()
    request = valid_request(query=query)

    response = execute_remote_query(request, StaticPostgresCheckRegistry([make_check(pool=pool)]))

    assert response['status'] == 'FAILED'
    assert response_code(response) == 'invalid_request'
    assert 'query' in response['error']['message']
    assert pool.requested_dbnames == []
