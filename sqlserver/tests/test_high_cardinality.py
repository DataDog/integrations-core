# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import threading
import time
from copy import copy

import pytest

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
@pytest.mark.run_high_cardinality_forever
def test_run_high_cardinality_forever(dbm_instance):
    """
    This test is a utility and is useful in situations where you want to connect to the database instance
    and have queries executing against it. Note, you must kill the test operation to stop this test.

    In order to run this test, you must pass the `--run_high_cardinality_forever` flag.
    e.g. `ddev ... -pa --run_high_cardinality_forever`

    TIP: It's more convenient to utilize this by running it as a standalone test operation.
    e.g. in conjunction with the required flag
    `ddev ... -pa --run_high_cardinality_forever -k test_run_high_cardinality_forever`
    """
    queries = HighCardinalityQueries(dbm_instance)
    queries.start_background('bob', config={'hc_threads': 20, 'slow_threads': 5, 'complex_threads': 10})


@high_cardinality_only
def test_complete_metrics_run(dd_run_check, dbm_instance, aggregator):
    dbm_instance['query_activity']['enabled'] = False
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    queries = HighCardinalityQueries(dbm_instance)

    def _run_queries_and_time_check():
        queries_to_create = 4000
        thread_count = 20
        hc_queries = [queries.create_high_cardinality_query() for _ in range(queries_to_create)]

        def _run_queries(idx):
            conn = queries.get_conn_for_user('bob')
            queries_to_run = queries_to_create // thread_count
            for q in hc_queries[idx * queries_to_run : (idx + 1) * queries_to_run]:
                conn.execute(q)

        threads = [threading.Thread(target=_run_queries, args=(i,)) for i in range(thread_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        start = time.time()
        dd_run_check(check)
        return time.time() - start

    # First run will load the test queries into the StatementMetrics state
    first_run_elapsed = _run_queries_and_time_check()
    # Second run will emit metrics based on the diff of the current and prev state
    second_run_elapsed = _run_queries_and_time_check()

    total_elapsed_time = first_run_elapsed + second_run_elapsed
    assert total_elapsed_time <= 15


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
