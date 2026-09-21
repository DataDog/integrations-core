# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import logging

from clickhouse_connect.driver.exceptions import OperationalError

from datadog_checks.clickhouse.remote_query import iter_agent_rpc_stream_events

from .remote_query_fakes import (
    FakeClickhouseClient,
    FakeUploadClient,
    assert_failed_event,
    assert_success,
    collect_events,
    event_metadata,
    make_check,
    make_client,
    patch_allowlist_disabled,
    patch_upload_credentials,
    stream_body,
    valid_request,
)


def test_stream_resolves_server_port_db_from_check_config(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = make_client(rows=[[1]])

    events = collect_events(valid_request(), make_check(), clickhouse_client=clickhouse_client)

    assert_success(events)


def test_stream_host_port_dbname_target_still_succeeds_when_check_has_database_identifier(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = make_client(rows=[[1]])
    check = make_check(check_database_identifier='clickhouse-dbi')

    events = collect_events(valid_request(), check, clickhouse_client=clickhouse_client)

    assert_success(events)


def test_stream_database_instance_match_runs_the_supplied_check(monkeypatch):
    patch_upload_credentials(monkeypatch)
    matching_client = make_client(rows=[[1]])
    check = make_check(server='analytics.internal', db='analytics', check_database_identifier='Clickhouse/Primary-A')

    request = valid_request()
    request['target'] = {'database_instance': 'Clickhouse/Primary-A'}
    events = collect_events(request, check, clickhouse_client=matching_client)

    assert_success(events)
    assert matching_client.raw_stream_calls


def test_stream_database_instance_miss_fails_without_client_access():
    clickhouse_client = make_client(rows=[[1]])
    check = make_check(check_database_identifier='Clickhouse/Primary-A')

    request = valid_request()
    request['target'] = {'database_instance': 'Clickhouse/Primary-B'}
    events = collect_events(request, check, clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'target_not_found')
    assert clickhouse_client.raw_stream_calls == []


def test_stream_missing_pool_manager_returns_target_unavailable(monkeypatch):
    patch_upload_credentials(monkeypatch)
    check = make_check()
    check._pool_manager = None

    events = collect_events(valid_request(), check)

    assert_failed_event(events, 'target_unavailable')


def test_stream_maps_transport_error_to_target_unavailable(monkeypatch, caplog):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    clickhouse_client = FakeClickhouseClient(
        stream_body(('value',), ('UInt8',), [[1]]),
        raw_stream_error=OperationalError('Error HTTPSConnectionPool ... SECRET_DO_NOT_LOG'),
    )

    caplog.set_level(logging.DEBUG)
    events = collect_events(valid_request(), make_check(), clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'target_unavailable')
    assert 'SECRET_DO_NOT_LOG' not in str(events)
    assert 'SECRET_DO_NOT_LOG' not in caplog.text


def test_stream_maps_client_creation_failure_to_target_unavailable(monkeypatch, caplog):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)

    def broken_factory(_check, _limits):
        raise OperationalError('connection refused with SECRET_DO_NOT_LOG')

    request = valid_request()
    caplog.set_level(logging.DEBUG)
    events = list(iter_agent_rpc_stream_events(request, make_check(), FakeUploadClient(), broken_factory))

    assert_failed_event(events, 'target_unavailable')
    assert 'SECRET_DO_NOT_LOG' not in str(events)
    assert 'SECRET_DO_NOT_LOG' not in caplog.text


def test_stream_target_unavailable_when_check_cannot_create_clients(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    # No create_remote_query_client on the fake check and no factory injected.
    request = valid_request()
    events = list(iter_agent_rpc_stream_events(request, make_check(), FakeUploadClient(), None))

    assert_failed_event(events, 'target_unavailable')
    assert 'upload_receipt' not in event_metadata(events[-1])
