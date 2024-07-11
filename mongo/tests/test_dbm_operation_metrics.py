# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os

import pytest

from . import common
from .common import HERE
from .conftest import mock_now, mock_pymongo, run_check_once

pytestmark = [pytest.mark.usefixtures('dd_environment'), pytest.mark.integration]


@mock_now(1715911398.1112723)
@common.standalone
def test_mongo_operation_metrics_standalone(aggregator, instance_integration_cluster, check, dd_run_check):
    instance_integration_cluster['dbm'] = True
    instance_integration_cluster['operation_metrics'] = {'enabled': True, 'run_sync': True}
    instance_integration_cluster['database_autodiscovery'] = {'enabled': True, 'include': ['integration$', 'test$']}

    mongo_check = check(instance_integration_cluster)
    aggregator.reset()
    with mock_pymongo("standalone"):
        run_check_once(mongo_check, dd_run_check)

    dbm_metrics = aggregator.get_event_platform_events("dbm-metrics")

    with open(os.path.join(HERE, "results", "operation-metrics-standalone.json"), 'r') as f:
        expected_metrics = json.load(f)
        assert dbm_metrics == expected_metrics


@mock_now(1715911398.1112723)
@common.shard
def test_mongo_operation_metrics_mongos(aggregator, instance_integration_cluster, check, dd_run_check):
    instance_integration_cluster['dbm'] = True
    instance_integration_cluster['operation_metrics'] = {'enabled': True, 'run_sync': True}
    instance_integration_cluster['database_autodiscovery'] = {'enabled': True, 'include': ['integration$', 'test$']}

    mongo_check = check(instance_integration_cluster)
    aggregator.reset()
    with mock_pymongo("mongos"):
        run_check_once(mongo_check, dd_run_check)

    dbm_metrics = aggregator.get_event_platform_events("dbm-metrics")

    # assert metrics
    with open(os.path.join(HERE, "results", "operation-metrics-mongos.json"), 'r') as f:
        expected_metrics = json.load(f)
        assert dbm_metrics == expected_metrics


@common.shard
def test_mongo_operation_metrics_arbiter(aggregator, instance_arbiter, check, dd_run_check):
    instance_arbiter['dbm'] = True
    instance_arbiter['cluster_name'] = 'my_cluster'
    instance_arbiter['operation_metrics'] = {'enabled': True, 'run_sync': True}

    mongo_check = check(instance_arbiter)
    aggregator.reset()
    with mock_pymongo("replica-arbiter"):
        dd_run_check(mongo_check)

    dbm_metrics = aggregator.get_event_platform_events("dbm-metrics")

    assert len(dbm_metrics) == 0
