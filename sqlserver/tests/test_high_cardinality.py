# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import time
from copy import copy

import pytest

from concurrent.futures.thread import ThreadPoolExecutor
from datadog_checks.sqlserver import SQLServer

from .common import CHECK_NAME
from .utils import HighCardinalityQueries, high_cardinality_only


@pytest.fixture
def dbm_instance(instance_docker):
    instance_docker['dbm'] = True
    instance_docker['query_metrics'] = {'enabled': True, 'run_sync': True}
    instance_docker['query_activity'] = {'enabled': True, 'run_sync': True}
    return copy(instance_docker)


@high_cardinality_only
def test_complete_metrics_run(dd_run_check, dbm_instance, aggregator):
    dbm_instance['query_activity']['enabled'] = False
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    queries = HighCardinalityQueries(dbm_instance)

    conn = queries.get_conn_for_user('bob')
    hc_queries = [queries.create_high_cardinality_query() for _ in range(4000)]

    def _run_queries_and_check():
        for q in hc_queries:
            conn.execute(q)
        start = time.time()
        dd_run_check(check)
        return time.time() - start

    # First run will load the test queries into the StatementMetrics state
    first_run_elapsed = _run_queries_and_check()
    # Second run will emit metrics based on the diff of the current and prev state
    second_run_elapsed = _run_queries_and_check()

    total_elapsed_time = first_run_elapsed + second_run_elapsed
    assert total_elapsed_time <= 0


@high_cardinality_only
@pytest.mark.skip(reason='skip until the metrics query is improved')
@pytest.mark.parametrize('job', ['query_metrics', 'query_activity'])
@pytest.mark.parametrize(
    'background_config',
    [
        {'hc_threads': 50, 'slow_threads': 0, 'complex_threads': 0},
        {'hc_threads': 0, 'slow_threads': 50, 'complex_threads': 0},
        {'hc_threads': 0, 'slow_threads': 0, 'complex_threads': 50},
    ],
)
def test_individual_dbm_jobs(dd_run_check, instance_docker, job, background_config):
    instance_docker['dbm'] = True
    instance_docker[job] = {'enabled': True, 'run_sync': True}
    check = SQLServer(CHECK_NAME, {}, [instance_docker])
    queries = HighCardinalityQueries(instance_docker)
    _run_check_against_high_cardinality(dd_run_check, check, queries, config=background_config)


@high_cardinality_only
@pytest.mark.skip(reason='skip until the metrics query is improved')
@pytest.mark.parametrize("dbm_enabled,", [True, False])
def test_check_against_hc(dd_run_check, dbm_instance, dbm_enabled):
    dbm_instance['dbm'] = dbm_enabled
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    queries = HighCardinalityQueries(dbm_instance)
    _run_check_against_high_cardinality(
        dd_run_check, check, queries, config={'hc_threads': 20, 'slow_threads': 5, 'complex_threads': 10}
    )


def _run_check_against_high_cardinality(
    dd_run_check, check, queries, config=None, user='bob', expected_time=15, delay=60
):
    try:
        queries.start_background(user, config=config)
        # Allow the database to build up queries in the background before proceeding
        time.sleep(delay)

        start = time.time()
        try:
            dd_run_check(check)
            dd_run_check(check)
        except Exception:
            logging.error(
                'Check threw an exception while running, this is likely due to a timeout from the metrics job and '
                'could indicate a performance regression.'
            )
        elapsed = time.time() - start
        assert elapsed <= expected_time, 'expected elapsed time for two check runs failed'
    finally:
        queries.stop()
        check.cancel()
