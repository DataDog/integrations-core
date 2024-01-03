# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import pytest

from datadog_checks.postgres.util import (
    ANALYZE_PROGRESS_METRICS,
    CLUSTER_VACUUM_PROGRESS_METRICS,
    INDEX_PROGRESS_METRICS,
    VACUUM_PROGRESS_METRICS,
)

from .common import DB_NAME, _get_expected_tags, _iterate_metric_name
from .utils import (
    _wait_for_value,
    kill_session,
    kill_vacuum,
    lock_table,
    requires_over_12,
    requires_over_13,
    run_query_thread,
    run_vacuum_thread,
)

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def _check_analyze_progress(check, pg_instance, table):
    thread = run_vacuum_thread(pg_instance, f'VACUUM ANALYZE {table}')

    # Wait for vacuum to be reported
    _wait_for_value(
        pg_instance,
        lower_threshold=0,
        query="SELECT count(*) from pg_stat_progress_analyze",
    )

    # Collect metrics
    check.check(pg_instance)

    # Kill vacuum and cleanup thread
    kill_vacuum(pg_instance)
    thread.join()


@requires_over_13
def test_analyze_progress_inherited(aggregator, integration_check, pg_instance):
    check = integration_check(pg_instance)
    _check_analyze_progress(check, pg_instance, 'test_part')
    expected_tags = _get_expected_tags(check, pg_instance) + [
        'child_relation:test_part1',
        'phase:acquiring inherited sample rows',
        'table:test_part',
        f'db:{DB_NAME}',
    ]
    for metric_name in _iterate_metric_name(ANALYZE_PROGRESS_METRICS):
        aggregator.assert_metric(metric_name, count=1, tags=expected_tags)


@requires_over_13
def test_analyze_progress(aggregator, integration_check, pg_instance):
    check = integration_check(pg_instance)
    _check_analyze_progress(check, pg_instance, 'test_part1')
    expected_tags = _get_expected_tags(check, pg_instance) + [
        'phase:acquiring sample rows',
        'table:test_part1',
        f'db:{DB_NAME}',
    ]
    for metric_name in _iterate_metric_name(ANALYZE_PROGRESS_METRICS):
        aggregator.assert_metric(metric_name, count=1, tags=expected_tags)


@requires_over_12
def test_vacuum_progress(aggregator, integration_check, pg_instance):
    check = integration_check(pg_instance)

    # Start vacuum
    thread = run_vacuum_thread(pg_instance, 'VACUUM (DISABLE_PAGE_SKIPPING) test_part1')

    # Wait for vacuum to be reported
    _wait_for_value(
        pg_instance,
        lower_threshold=0,
        query="SELECT count(*) from pg_stat_progress_vacuum",
    )

    # Collect metrics
    check.check(pg_instance)

    # Kill vacuum and cleanup thread
    kill_vacuum(pg_instance)
    thread.join()

    expected_tags = _get_expected_tags(check, pg_instance) + [
        'phase:scanning heap',
        'table:test_part1',
        f'db:{DB_NAME}',
    ]
    for metric_name in _iterate_metric_name(VACUUM_PROGRESS_METRICS):
        aggregator.assert_metric(metric_name, count=1, tags=expected_tags)


@requires_over_12
def test_index_progress(aggregator, integration_check, pg_instance):
    check = integration_check(pg_instance)

    # Keep test_part locked to prevent create index concurrently from finishing
    conn = lock_table(pg_instance, 'test_part1', 'ROW EXCLUSIVE')

    # Start vacuum in a thread
    thread = run_query_thread(pg_instance, 'CREATE INDEX CONCURRENTLY test_progress_index ON test_part1 (id);')

    # Wait for blocked created index to appear
    _wait_for_value(
        pg_instance,
        lower_threshold=0,
        query="select count(*) FROM pg_stat_progress_create_index where lockers_total=1;",
    )
    # Gather metrics
    check.check(pg_instance)

    # Kill the create index
    kill_session(pg_instance, 'CREATE INDEX')

    # Cleanup connection and thread
    conn.close()
    thread.join()

    # Check metrics
    expected_tags = _get_expected_tags(check, pg_instance) + [
        'command:CREATE INDEX CONCURRENTLY',
        'index:test_progress_index',
        'phase:waiting for writers before build',
        'table:test_part1',
        f'db:{DB_NAME}',
    ]
    for metric_name in _iterate_metric_name(INDEX_PROGRESS_METRICS):
        aggregator.assert_metric(metric_name, count=1, tags=expected_tags)
    aggregator.assert_metric('postgresql.create_index.lockers_total', count=1, value=1, tags=expected_tags)


@requires_over_12
def test_cluster_vacuum_progress(aggregator, integration_check, pg_instance):
    check = integration_check(pg_instance)

    # Keep pg_class lock to block vacuum full during initilizing phase
    conn = lock_table(pg_instance, 'pg_catalog.pg_class', 'EXCLUSIVE')

    # Start vacuum in a thread
    thread = run_vacuum_thread(pg_instance, 'VACUUM FULL personsdup1')

    _wait_for_value(pg_instance, lower_threshold=0, query="select count(*) FROM pg_stat_progress_cluster;")
    check.check(pg_instance)

    # Cleanup connection and thread
    conn.close()
    thread.join()

    expected_tags = _get_expected_tags(check, pg_instance) + [
        'phase:initializing',
        'command:VACUUM FULL',
        'table:personsdup1',
        f'db:{DB_NAME}',
    ]
    for metric_name in _iterate_metric_name(CLUSTER_VACUUM_PROGRESS_METRICS):
        aggregator.assert_metric(metric_name, count=1, tags=expected_tags)
