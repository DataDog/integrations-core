# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json

import pytest

from datadog_checks.postgres.remote_query import StaticPostgresCheckRegistry, iter_agent_rpc_stream_copy_events


def remote_query_copy_request(
    pg_instance: dict[str, object], query: str, limits: dict[str, int], stream_format: str = 'csv'
) -> dict[str, object]:
    return {
        'operation': 'copy_stream',
        'target': {
            'host': pg_instance['host'],
            'port': int(pg_instance['port']),
            'dbname': pg_instance['dbname'],
        },
        'query': query,
        'format': stream_format,
        'limits': limits,
    }


def event_metadata(event):
    return event.metadata


def event_payload(event):
    return event.payload


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_agent_local_copy_stream_select_1_reuses_integration_check_credentials(integration_check, pg_instance):
    check = integration_check(pg_instance)
    request = remote_query_copy_request(
        pg_instance,
        'SELECT 1 AS value',
        {'chunkBytes': 16, 'maxBytes': 1024, 'maxRowBytes': 128, 'timeoutMs': 5000},
    )

    events = list(iter_agent_rpc_stream_copy_events(request, StaticPostgresCheckRegistry([check])))

    data = b''.join(event_payload(event) for event in events if event.event_type == 'data')
    assert events[0].event_type == 'metadata'
    assert event_metadata(events[0])['operation'] == 'copy_stream'
    assert event_metadata(events[-1])['status'] == 'SUCCEEDED'
    assert data == b'1\n'
    assert event_metadata(events[-1])['stats']['bytesEmitted'] == len(data)
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

    data_events = [event for event in events if event.event_type == 'data']
    data = b''.join(event_payload(event) for event in data_events)
    assert events[0].event_type == 'metadata'
    assert event_metadata(events[0])['format'] == 'csv'
    assert event_metadata(events[-1])['status'] == 'SUCCEEDED'
    assert b'Beautiful city of lights,France\n' in data
    assert b'New York,USA\n' in data
    assert event_metadata(events[-1])['stats']['bytesEmitted'] == len(data)
    assert all(event_metadata(event)['bytes'] <= 16 for event in data_events)
    assert 'password' not in json.dumps(request).lower()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_agent_local_copy_stream_binary_format_preserves_non_text_bytes(integration_check, pg_instance):
    check = integration_check(pg_instance)
    request = remote_query_copy_request(
        pg_instance,
        "SELECT decode('00ff80', 'hex') AS payload",
        {'chunkBytes': 1024, 'maxBytes': 4096, 'maxRowBytes': 4096, 'timeoutMs': 5000},
        stream_format='binary',
    )

    events = list(iter_agent_rpc_stream_copy_events(request, StaticPostgresCheckRegistry([check])))

    data = b''.join(event_payload(event) for event in events if event.event_type == 'data')
    assert events[0].event_type == 'metadata'
    assert event_metadata(events[0])['format'] == 'binary'
    assert event_metadata(events[-1])['status'] == 'SUCCEEDED'
    assert b'PGCOPY\n\xff\r\n\x00' in data
    assert b'\x00\xff\x80' in data


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_agent_local_copy_stream_enforces_max_row_bytes_and_connection_remains_reusable(integration_check, pg_instance):
    check = integration_check(pg_instance)
    oversized_request = remote_query_copy_request(
        pg_instance,
        "SELECT repeat('x', 1048576) AS payload",
        {'chunkBytes': 1024, 'maxBytes': 2 * 1048576, 'maxRowBytes': 1024, 'timeoutMs': 5000},
    )

    events = list(iter_agent_rpc_stream_copy_events(oversized_request, StaticPostgresCheckRegistry([check])))

    assert [event for event in events if event.event_type == 'data'] == []
    assert event_metadata(events[-1])['status'] == 'FAILED'
    assert event_metadata(events[-1])['error']['code'] == 'max_row_bytes_exceeded'

    reusable_request = remote_query_copy_request(
        pg_instance,
        'SELECT 1 AS value',
        {'chunkBytes': 16, 'maxBytes': 1024, 'maxRowBytes': 128, 'timeoutMs': 5000},
    )
    reusable_events = list(iter_agent_rpc_stream_copy_events(reusable_request, StaticPostgresCheckRegistry([check])))
    reusable_data = b''.join(event_payload(event) for event in reusable_events if event.event_type == 'data')
    assert event_metadata(reusable_events[-1])['status'] == 'SUCCEEDED'
    assert reusable_data == b'1\n'
