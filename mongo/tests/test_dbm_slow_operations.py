# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os

import pytest

from . import common
from .common import HERE
from .conftest import mock_now, mock_pymongo
from .utils import assert_metrics, run_check_once

pytestmark = [pytest.mark.usefixtures('dd_environment'), pytest.mark.integration]


@mock_now(1715911398.1112723)
@common.standalone
def test_mongo_slow_operations_standalone(aggregator, instance_integration_cluster, check, dd_run_check):
    instance_integration_cluster['reported_database_hostname'] = "mongohost"
    instance_integration_cluster['dbm'] = True
    instance_integration_cluster['slow_operations'] = {'enabled': True, 'run_sync': True}
    instance_integration_cluster['database_autodiscovery'] = {'enabled': True, 'include': ['integration$', 'test$']}

    mongo_check = check(instance_integration_cluster)
    aggregator.reset()
    with mock_pymongo("standalone"):
        run_check_once(mongo_check, dd_run_check)

    events = aggregator.get_event_platform_events("dbm-activity")
    slow_operations = [event for event in events if event['dbm_type'] == 'slow_query']
    print(json.dumps(slow_operations))

    with open(os.path.join(HERE, "results", "slow-operations-standalone.json"), 'r') as f:
        expected_slow_operations = json.load(f)
        assert slow_operations == expected_slow_operations

    assert_metrics(
        mongo_check,
        aggregator,
        ["profiling"],
    )


@mock_now(1715911398.1112723)
@common.shard
def test_mongo_slow_operations_mongos(aggregator, instance_integration_cluster, check, dd_run_check):
    instance_integration_cluster['reported_database_hostname'] = "mongohost"
    instance_integration_cluster['dbm'] = True
    instance_integration_cluster['slow_operations'] = {'enabled': True, 'run_sync': True}
    instance_integration_cluster['database_autodiscovery'] = {'enabled': True, 'include': ['integration$', 'test$']}

    mongo_check = check(instance_integration_cluster)
    aggregator.reset()
    with mock_pymongo("mongos"):
        run_check_once(mongo_check, dd_run_check)

    events = aggregator.get_event_platform_events("dbm-activity")
    slow_operations = [event for event in events if event['dbm_type'] == 'slow_query']
    print(json.dumps(slow_operations))

    with open(os.path.join(HERE, "results", "slow-operations-mongos.json"), 'r') as f:
        expected_slow_operations = json.load(f)
        assert slow_operations == expected_slow_operations


@common.shard
def test_mongo_slow_operations_arbiter(aggregator, instance_arbiter, check, dd_run_check):
    instance_arbiter['dbm'] = True
    instance_arbiter['cluster_name'] = 'my_cluster'
    instance_arbiter['slow_operations'] = {'enabled': True, 'run_sync': True}

    mongo_check = check(instance_arbiter)
    aggregator.reset()
    with mock_pymongo("replica-arbiter"):
        dd_run_check(mongo_check)

    events = aggregator.get_event_platform_events("dbm-samples")
    slow_operations = [event for event in events if event['dbm_type'] == 'slow_query']

    assert len(slow_operations) == 0
