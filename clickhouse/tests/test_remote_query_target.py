# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import logging
import subprocess
import sys

import pytest
from clickhouse_connect.driver.exceptions import OperationalError

from datadog_checks.clickhouse.remote_query import ClickhouseRemoteQueryHandler

from .remote_query_fakes import (
    ExplodingCheck,
    FakeClickhouseClient,
    FakeUploadClient,
    assert_failed_event,
    assert_matched_verdict,
    assert_success,
    collect_events,
    collect_resolve_events,
    event_metadata,
    forbidding_client_factory,
    make_check,
    make_client,
    patch_allowlist_disabled,
    patch_upload_credentials,
    resolve_request,
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
    events = list(
        ClickhouseRemoteQueryHandler(make_check()).execute(
            request, http_client=FakeUploadClient(), clickhouse_client_factory=broken_factory
        )
    )

    assert_failed_event(events, 'target_unavailable')
    assert 'SECRET_DO_NOT_LOG' not in str(events)
    assert 'SECRET_DO_NOT_LOG' not in caplog.text


def test_stream_target_unavailable_when_check_cannot_create_clients(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    # No create_remote_query_client on the fake check and no factory injected.
    request = valid_request()
    events = list(ClickhouseRemoteQueryHandler(make_check()).execute(request, http_client=FakeUploadClient()))

    assert_failed_event(events, 'target_unavailable')
    assert 'upload_receipt' not in event_metadata(events[-1])


def test_resolve_verdict_reports_sanitized_match_identity():
    check = make_check(check_database_identifier='Clickhouse/Primary-A')

    events = collect_resolve_events(resolve_request(), check)

    match = assert_matched_verdict(events)
    assert match == {
        'host': 'localhost',
        'port': 8123,
        'configuredDbname': 'default',
        'resolvedDbname': 'default',
        'databaseInstance': 'Clickhouse/Primary-A',
    }


def test_resolve_verdict_completes_without_creating_a_query_client():
    """Resolution reads the check's configuration alone: the matched verdict is emitted with
    no query client — hence no SQL executed anywhere — because the check's only client
    creation hook fails the test on touch."""
    check = make_check(check_database_identifier='Clickhouse/Primary-A')
    check.create_remote_query_client = forbidding_client_factory()

    events = collect_resolve_events(resolve_request(), check)

    assert_matched_verdict(events)


def test_resolve_no_match_never_probes_the_requested_database():
    """A different database on the configured endpoint is not a match, and resolution never
    creates a client to probe it: a database that exists elsewhere and one that does not
    are indistinguishable by design."""
    check = make_check(check_database_identifier='Clickhouse/Primary-A')
    check.create_remote_query_client = forbidding_client_factory()

    events = collect_resolve_events(resolve_request(dbname='unconfigured_existing_or_missing'), check)

    assert len(events) == 1
    assert_failed_event(events, 'target_not_found')


def test_resolve_database_instance_verdict_reports_materialized_configured_dbname():
    check = make_check(server='analytics.internal', db='analytics', check_database_identifier='Clickhouse/Primary-A')
    check.create_remote_query_client = forbidding_client_factory()

    events = collect_resolve_events(resolve_request(database_instance='Clickhouse/Primary-A'), check)

    match = assert_matched_verdict(events)
    assert match['configuredDbname'] == match['resolvedDbname'] == 'analytics'
    assert match['databaseInstance'] == 'Clickhouse/Primary-A'
    assert match['host'] == 'analytics.internal'
    assert match['port'] == 8123


def test_resolve_database_instance_without_configured_dbname_fails_target_unavailable():
    """A matched check that cannot name its database is an error other than target_not_found,
    so the Agent fails its aggregate resolution instead of skipping the check."""
    check = make_check(db=None, check_database_identifier='Clickhouse/Primary-A')

    events = collect_resolve_events(resolve_request(database_instance='Clickhouse/Primary-A'), check)

    assert len(events) == 1
    assert_failed_event(events, 'target_unavailable', 'configured database name')


@pytest.mark.parametrize(
    'invalid_request',
    [
        {'operation': 'resolve_target'},
        {'operation': 'resolve_target', 'query': 'SELECT 1'},
        {'operation': 'resolve_target', 'target': {'database_instance': 'x', 'host': 'h', 'port': 1, 'dbname': 'd'}},
    ],
)
def test_resolve_rejects_invalid_requests_before_matching(invalid_request):
    """Resolve carries the operation and target only: every other field, a missing target,
    and a target mixing both selector modes are rejected before any matching, without
    echoing the offending request text."""
    events = collect_resolve_events(invalid_request, ExplodingCheck())

    assert_failed_event(events, 'invalid_request')
    assert 'SELECT 1' not in str(events)


def test_resolve_and_execute_share_the_same_matching_authority(monkeypatch):
    """The resolve verdict must predict execution: a target that resolves MATCHED on one
    check executes on it, and one that resolves target_not_found never executes."""
    patch_upload_credentials(monkeypatch)
    matching_client = make_client(rows=[[1]])
    check = make_check(check_database_identifier='Clickhouse/Primary-A')

    assert_matched_verdict(collect_resolve_events(resolve_request(), check))
    events = collect_events(valid_request(), check, clickhouse_client=matching_client)
    assert_success(events)
    assert matching_client.raw_stream_calls

    other_client = make_client(rows=[[1]])
    assert_failed_event(collect_resolve_events(resolve_request(dbname='other_db'), check), 'target_not_found')
    events = collect_events(valid_request(dbname='other_db'), check, clickhouse_client=other_client)
    assert_failed_event(events, 'target_not_found')
    assert other_client.raw_stream_calls == []


def test_importing_the_check_does_not_import_the_remote_query_runtime():
    """Ordinary monitoring startup stays free of the optional remote-query runtime: the
    capability hook builds its handler behind a function-local import, so importing the
    check module alone must not import it.

    The assertion runs in a fresh interpreter because this suite (in any test ordering)
    imports the runtime module into its own `sys.modules`.
    """
    code = (
        "import sys; from datadog_checks.clickhouse import ClickhouseCheck; "
        "assert 'datadog_checks.clickhouse.remote_query' not in sys.modules"
    )
    subprocess.run([sys.executable, '-c', code], check=True)
