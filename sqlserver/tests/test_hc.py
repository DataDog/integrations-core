# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time
from copy import copy

import pytest

from datadog_checks.sqlserver import SQLServer

from .utils import HcQueries, hc_only

try:
    import pyodbc
except ImportError:
    pyodbc = None


CHECK_NAME = "sqlserver"


@pytest.fixture
def dbm_instance(instance_docker):
    instance_docker['dbm'] = True
    # Run everything at its default value to resemble actual use
    instance_docker['query_metrics'] = {'enabled': True, 'run_sync': False, 'collection_interval': 10}
    instance_docker['query_activity'] = {'enabled': True, 'run_sync': False, 'collection_interval': 10}
    return copy(instance_docker)


@hc_only
def test_hc_completion(dd_run_check, dbm_instance, instance_docker):
    instance_docker['query_metrics']['run_sync'] = True
    instance_docker['query_activity']['run_sync'] = True
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    queries = HcQueries(instance_docker)
    try:
        queries.run_hc_queries('bob', config={'hc_threads': 20, 'slow_threads': 5})
        # Allow the database to build up some queries before proceeding
        time.sleep(60)

        start = time.time()
        dd_run_check(check)
        elapsed = time.time() - start
        assert elapsed <= 15
    finally:
        queries.stop_queries()
        check.cancel()
