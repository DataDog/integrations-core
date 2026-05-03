# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json

import pytest

from datadog_checks.postgres.remote_query import (
    StaticPostgresCheckRegistry,
    execute_remote_query,
    iter_agent_rpc_stream_copy_events,
)


def remote_query_request(pg_instance: dict[str, object], query: str) -> dict[str, object]:
    return {
        'target': {
            'host': pg_instance['host'],
            'port': int(pg_instance['port']),
            'dbname': pg_instance['dbname'],
        },
        'query': query,
        'limits': {'maxRows': 10, 'maxBytes': 1048576, 'timeoutMs': 5000},
    }


def remote_query_copy_request(pg_instance: dict[str, object], query: str, limits: dict[str, int]) -> dict[str, object]:
    return {
        'operation': 'copy_stream',
        'target': {
            'host': pg_instance['host'],
            'port': int(pg_instance['port']),
            'dbname': pg_instance['dbname'],
        },
        'query': query,
        'format': 'csv',
        'limits': limits,
    }


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_agent_local_executor_select_1_reuses_integration_check_credentials(integration_check, pg_instance):
    check = integration_check(pg_instance)
    request = remote_query_request(pg_instance, 'SELECT 1 AS value')

    response = execute_remote_query(request, StaticPostgresCheckRegistry([check]))

    assert response['status'] == 'SUCCEEDED'
    assert response['columns'][0]['name'] == 'value'
    assert response['rows'] == [{'value': 1}]
    assert response['truncated'] is False
    assert response['stats']['rowCount'] == 1
    assert 'password' not in json.dumps(request).lower()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_agent_local_executor_fixture_table_query_returns_city_rows(integration_check, pg_instance):
    bob_instance = dict(pg_instance, username='bob', password='bob')
    check = integration_check(bob_instance)
    request = remote_query_request(bob_instance, 'SELECT city, country FROM cities ORDER BY city')

    response = execute_remote_query(request, StaticPostgresCheckRegistry([check]))

    assert response['status'] == 'SUCCEEDED'
    assert response['columns'] == [{'name': 'city', 'type': 'string'}, {'name': 'country', 'type': 'string'}]
    assert response['rows'] == [
        {'city': 'Beautiful city of lights', 'country': 'France'},
        {'city': 'New York', 'country': 'USA'},
    ]
    assert response['truncated'] is False
    assert response['stats']['rowCount'] == 2
    assert 'password' not in json.dumps(request).lower()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_agent_local_copy_stream_fixture_table_query_emits_csv_chunks(integration_check, pg_instance):
    bob_instance = dict(pg_instance, username='bob', password='bob')
    check = integration_check(bob_instance)
    request = remote_query_copy_request(
        bob_instance,
        'SELECT city, country FROM cities ORDER BY city',
        {'chunkBytes': 16, 'maxBytes': 1024, 'maxRowBytes': 128, 'timeoutMs': 5000},
    )

    events = list(iter_agent_rpc_stream_copy_events(request, StaticPostgresCheckRegistry([check])))

    data = b''.join(event['data'] for event in events if event['type'] == 'data')
    assert events[0]['type'] == 'metadata'
    assert events[0]['format'] == 'csv'
    assert events[-1]['status'] == 'SUCCEEDED'
    assert b'Beautiful city of lights,France\n' in data
    assert b'New York,USA\n' in data
    assert events[-1]['stats']['bytesEmitted'] == len(data)
    assert all(event['bytes'] <= 16 for event in events if event['type'] == 'data')
    assert 'password' not in json.dumps(request).lower()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_agent_local_copy_stream_enforces_max_row_bytes_and_reuses_connection(integration_check, pg_instance):
    check = integration_check(pg_instance)
    request = remote_query_copy_request(
        pg_instance,
        "SELECT repeat('x', 1048576) AS payload",
        {'chunkBytes': 1024, 'maxBytes': 2 * 1048576, 'maxRowBytes': 1024, 'timeoutMs': 5000},
    )

    events = list(iter_agent_rpc_stream_copy_events(request, StaticPostgresCheckRegistry([check])))

    assert [event for event in events if event['type'] == 'data'] == []
    assert events[-1]['status'] == 'FAILED'
    assert events[-1]['error']['code'] == 'max_row_bytes_exceeded'

    response = execute_remote_query(
        remote_query_request(pg_instance, 'SELECT 1 AS value'), StaticPostgresCheckRegistry([check])
    )
    assert response['status'] == 'SUCCEEDED'
    assert response['rows'] == [{'value': 1}]
