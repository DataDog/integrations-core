# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import logging

import psycopg.errors as psycopg_errors
import pytest

from datadog_checks.base.utils.remote_queries import contract as rq_contract
from datadog_checks.postgres.remote_query import PostgresRemoteQueryHandler

from .remote_query_fakes import (
    FakeAutodiscovery,
    FakePool,
    FakeUploadClient,
    assert_failed_event,
    assert_matched_verdict,
    assert_success,
    collect_events,
    collect_resolve_events,
    event_metadata,
    make_check,
    patch_allowlist_disabled,
    patch_upload_credentials,
    resolve_request,
    valid_request,
)


def test_stream_resolves_exact_host_port_dbname_from_check_config(monkeypatch):
    patch_upload_credentials(monkeypatch)
    pool = FakePool(rows=[(1,)])
    check = make_check(host='localhost', port=5432, dbname='datadog_test', pool=pool)

    events = collect_events(valid_request(), check, client=FakeUploadClient())

    assert_success(events)
    assert pool.requested_dbnames == ['datadog_test']


def test_stream_host_port_dbname_target_still_succeeds_when_check_has_database_identifier(monkeypatch):
    patch_upload_credentials(monkeypatch)
    pool = FakePool(rows=[(1,)])
    check = make_check(
        host='localhost',
        port=5432,
        dbname='datadog_test',
        pool=pool,
        check_database_identifier='postgres-dbi',
    )

    events = collect_events(valid_request(), check, client=FakeUploadClient())

    assert_success(events)
    assert pool.requested_dbnames == ['datadog_test']


def test_stream_database_instance_match_runs_on_the_check_configured_database(monkeypatch):
    patch_upload_credentials(monkeypatch)
    matching_pool = FakePool(rows=[(1,)])
    check = make_check(dbname='analytics', pool=matching_pool, check_database_identifier='Postgres/Primary-A')

    request = valid_request()
    request['target'] = {'database_instance': 'Postgres/Primary-A'}
    events = collect_events(request, check, client=FakeUploadClient())

    assert_success(events)
    # A database_instance selector admits the matched check's materialized configured
    # database, never a request-named other one.
    assert matching_pool.requested_dbnames == ['analytics']


def test_stream_database_instance_miss_fails_without_pool_access():
    pool = FakePool(rows=[(1,)])
    check = make_check(pool=pool, check_database_identifier='Postgres/Primary-A')

    request = valid_request()
    request['target'] = {'database_instance': 'Postgres/Primary-B'}
    events = collect_events(request, check)

    assert_failed_event(events, 'target_not_found')
    assert pool.requested_dbnames == []


def test_stream_host_port_dbname_target_ignores_database_instance_matches():
    pool = FakePool(rows=[(1,)])
    check = make_check(
        host='configured.internal',
        port=5432,
        dbname='datadog_test',
        pool=pool,
        reported_hostname='reported.internal',
        check_database_identifier='reported.internal',
    )

    events = collect_events(valid_request(host='reported.internal'), check)

    assert_failed_event(events, 'target_not_found')
    assert pool.requested_dbnames == []


def test_stream_closed_pool_returns_target_unavailable_without_recreating_credentials(monkeypatch):
    patch_upload_credentials(monkeypatch)
    pool = FakePool(closed=True)

    events = collect_events(valid_request(), make_check(pool=pool), client=FakeUploadClient())

    assert_failed_event(events, 'target_unavailable')
    assert pool.requested_dbnames == []


def test_stream_tuple_target_never_defaults_a_missing_configured_dbname(monkeypatch):
    """The adapter consumes the materialized config dbname only; it must not re-derive the
    integration's omitted-dbname default itself, or a check whose config never materialized
    a database would match a request naming the default."""
    patch_upload_credentials(monkeypatch)
    pool = FakePool(rows=[(1,)])
    check = make_check(host='localhost', port=5432, dbname=None, pool=pool)

    events = collect_events(valid_request(dbname='postgres'), check)

    assert_failed_event(events, 'target_not_found')
    assert pool.requested_dbnames == []


def test_stream_tuple_target_out_of_scope_database_fails_without_pool_access(monkeypatch):
    """A database outside the configured scope is not a match even when the endpoint matches.

    A database that exists but is unconfigured and a database that does not exist are
    deliberately indistinguishable: resolution never connects to the requested database or
    probes its name, so it cannot (and must not) distinguish them.
    """
    patch_upload_credentials(monkeypatch)
    pool = FakePool(rows=[(1,)])
    check = make_check(host='localhost', port=5432, dbname='production_ok', pool=pool)

    events = collect_events(valid_request(dbname='unconfigured_existing_or_missing'), check)

    assert_failed_event(events, 'target_not_found')
    assert pool.requested_dbnames == []
    assert not pool.cursors
    assert [event.event_type for event in events] == ['error']


def test_stream_tuple_target_matches_current_autodiscovered_database(monkeypatch):
    """With autodiscovery enabled, the eligible set is the check's own admitted discovery set."""
    patch_upload_credentials(monkeypatch)
    pool = FakePool(rows=[(1,)])
    autodiscovery = FakeAutodiscovery(databases=['dogs_0', 'dogs_1'])
    # Autodiscovery with an omitted dbname materializes the global view db as the configured
    # dbname; the request names an autodiscovered database instead.
    check = make_check(host='localhost', port=5432, dbname='postgres', pool=pool, autodiscovery=autodiscovery)

    events = collect_events(valid_request(dbname='dogs_1'), check, client=FakeUploadClient())

    assert_success(events)
    assert autodiscovery.get_items_calls == 1
    # Execution runs on the matched database only; no connection is opened anywhere else.
    assert pool.requested_dbnames == ['dogs_1']


def test_stream_tuple_target_excluded_by_autodiscovery_fails_without_pool_access(monkeypatch):
    """A database the check's own autodiscovery filters out is out of scope."""
    patch_upload_credentials(monkeypatch)
    pool = FakePool(rows=[(1,)])
    autodiscovery = FakeAutodiscovery(databases=['dogs_0', 'dogs_1'])
    check = make_check(host='localhost', port=5432, dbname='postgres', pool=pool, autodiscovery=autodiscovery)

    events = collect_events(valid_request(dbname='dogs_5'), check)

    assert_failed_event(events, 'target_not_found')
    assert autodiscovery.get_items_calls == 1
    assert pool.requested_dbnames == []
    assert not pool.cursors


def test_stream_scope_evaluated_only_for_endpoint_matching_checks():
    """Only an endpoint-matching check is scope-evaluated, so an undeterminable discovery set
    on an unrelated check can neither fail nor widen an unrelated request."""
    pool = FakePool(rows=[(1,)])
    other_autodiscovery = FakeAutodiscovery(error=psycopg_errors.OperationalError('discovery broke'))
    check = make_check(
        host='other.internal', port=5432, dbname='postgres', pool=pool, autodiscovery=other_autodiscovery
    )
    request = valid_request(dbname='dogs_1')

    events = collect_events(request, check)

    assert_failed_event(events, 'target_not_found')
    assert other_autodiscovery.get_items_calls == 0
    assert pool.requested_dbnames == []


def test_stream_autodiscovery_failure_is_visible_retryable_target_unavailable(monkeypatch, caplog):
    """An undeterminable discovery set fails closed and visibly, never as a silent no-match."""
    patch_upload_credentials(monkeypatch)
    pool = FakePool(rows=[(1,)])
    autodiscovery = FakeAutodiscovery(error=psycopg_errors.OperationalError('discovery broke: SECRET_DO_NOT_LOG'))
    check = make_check(host='localhost', port=5432, dbname='postgres', pool=pool, autodiscovery=autodiscovery)

    caplog.set_level(logging.DEBUG)
    events = collect_events(valid_request(dbname='dogs_1'), check)

    assert_failed_event(events, 'target_unavailable', 'autodiscovered database scope')
    assert event_metadata(events[-1])['error']['retryable'] is True
    assert autodiscovery.get_items_calls == 1
    # The customer's SQL never ran: no connection, no cursor, no upload session.
    assert pool.requested_dbnames == []
    assert not pool.cursors
    assert [event.event_type for event in events] == ['error']
    # The discovery failure's text never reaches the error event or the logs.
    assert 'SECRET_DO_NOT_LOG' not in str(events)
    assert 'SECRET_DO_NOT_LOG' not in caplog.text


def test_scope_failure_wrapper_keeps_no_path_back_to_the_discovery_exception():
    """The target_unavailable wrapper severs the discovery exception from its chain: a
    later traceback log of the wrapper can only ever see the fixed classification message,
    never the connection strings or identifiers the discovery error can quote."""
    autodiscovery = FakeAutodiscovery(error=psycopg_errors.OperationalError('discovery broke: SECRET_DO_NOT_LOG'))
    check = make_check(dbname='postgres', autodiscovery=autodiscovery)

    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        PostgresRemoteQueryHandler(check)._database_in_monitoring_scope('dogs_1')

    assert failure.value.code == 'target_unavailable'
    assert failure.value.retryable
    assert failure.value.__cause__ is None
    assert 'SECRET_DO_NOT_LOG' not in str(failure.value)


def test_stream_database_instance_without_configured_dbname_fails_target_unavailable(monkeypatch):
    patch_upload_credentials(monkeypatch)
    pool = FakePool(rows=[(1,)])
    check = make_check(dbname=None, pool=pool, check_database_identifier='Postgres/Primary-A')
    request = valid_request()
    request['target'] = {'database_instance': 'Postgres/Primary-A'}

    events = collect_events(request, check, client=FakeUploadClient())

    assert_failed_event(events, 'target_unavailable', 'configured database name')
    assert pool.requested_dbnames == []


def test_resolve_verdict_reports_sanitized_match_identity():
    pool = FakePool(rows=[(1,)])
    check = make_check(pool=pool, check_database_identifier='Postgres/Primary-A')

    events = collect_resolve_events(resolve_request(), check)

    match = assert_matched_verdict(events)
    assert match == {
        'host': 'localhost',
        'port': 5432,
        'configuredDbname': 'datadog_test',
        'resolvedDbname': 'datadog_test',
        'databaseInstance': 'Postgres/Primary-A',
    }
    # Resolve is side-effect free: no connection, no cursor, no upload session.
    assert pool.requested_dbnames == []
    assert not pool.cursors


def test_resolve_verdict_reports_autodiscovered_database_with_configured_dbname():
    """The verdict distinguishes the requested autodiscovered database from the configured one."""
    pool = FakePool(rows=[(1,)])
    autodiscovery = FakeAutodiscovery(databases=['dogs_0', 'dogs_1'])
    check = make_check(dbname='postgres', pool=pool, autodiscovery=autodiscovery)

    events = collect_resolve_events(resolve_request(dbname='dogs_1'), check)

    match = assert_matched_verdict(events)
    assert match['configuredDbname'] == 'postgres'
    assert match['resolvedDbname'] == 'dogs_1'
    assert pool.requested_dbnames == []


def test_resolve_no_match_is_one_target_not_found_error():
    """Out-of-scope and missing databases share the same verdict: target_not_found."""
    pool = FakePool(rows=[(1,)])
    check = make_check(dbname='production_ok', pool=pool)

    events = collect_resolve_events(resolve_request(dbname='unconfigured_existing_or_missing'), check)

    assert len(events) == 1
    assert_failed_event(events, 'target_not_found')
    assert pool.requested_dbnames == []
    assert not pool.cursors


def test_resolve_database_instance_verdict_reports_materialized_configured_dbname():
    check = make_check(dbname='production_ok', check_database_identifier='Postgres/Primary-A')

    events = collect_resolve_events(resolve_request(database_instance='Postgres/Primary-A'), check)

    match = assert_matched_verdict(events)
    assert match['configuredDbname'] == match['resolvedDbname'] == 'production_ok'
    assert match['databaseInstance'] == 'Postgres/Primary-A'


def test_resolve_database_instance_without_configured_dbname_fails_target_unavailable():
    """A matched check that cannot name its database is an error other than target_not_found,
    so the Agent fails its aggregate resolution instead of skipping the check."""
    check = make_check(dbname=None, check_database_identifier='Postgres/Primary-A')

    events = collect_resolve_events(resolve_request(database_instance='Postgres/Primary-A'), check)

    assert len(events) == 1
    assert_failed_event(events, 'target_unavailable', 'configured database name')


def test_resolve_discovery_failure_is_visible_target_unavailable():
    """An undeterminable eligible set is an error other than target_not_found: the check is
    never silently skipped from the Agent's sweep."""
    pool = FakePool(rows=[(1,)])
    autodiscovery = FakeAutodiscovery(error=psycopg_errors.OperationalError('discovery broke'))
    check = make_check(dbname='postgres', pool=pool, autodiscovery=autodiscovery)

    events = collect_resolve_events(resolve_request(dbname='dogs_1'), check)

    assert len(events) == 1
    assert_failed_event(events, 'target_unavailable', 'autodiscovered database scope')
    assert event_metadata(events[-1])['error']['retryable'] is True
    assert autodiscovery.get_items_calls == 1
    assert pool.requested_dbnames == []


def test_resolve_and_execute_share_the_same_matching_authority(monkeypatch):
    """The resolve verdict must predict execution: a target that resolves MATCHED on one
    check executes on it, and one that resolves target_not_found never executes."""
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[(1,)])
    autodiscovery = FakeAutodiscovery(databases=['dogs_0'])
    check = make_check(dbname='postgres', pool=pool, autodiscovery=autodiscovery)

    assert_matched_verdict(list(PostgresRemoteQueryHandler(check).resolve(resolve_request(dbname='dogs_0'))))
    events = collect_events(valid_request(dbname='dogs_0'), check, client=FakeUploadClient())
    assert_success(events)
    assert pool.requested_dbnames == ['dogs_0']

    assert_failed_event(
        list(PostgresRemoteQueryHandler(check).resolve(resolve_request(dbname='dogs_9'))), 'target_not_found'
    )
    events = collect_events(valid_request(dbname='dogs_9'), check, client=FakeUploadClient())
    assert_failed_event(events, 'target_not_found')
    assert pool.requested_dbnames == ['dogs_0']
