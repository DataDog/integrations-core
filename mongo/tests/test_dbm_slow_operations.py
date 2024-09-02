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
def test_mongo_slow_operations_standalone(aggregator, instance_integration_cluster_autodiscovery, check, dd_run_check):
    instance_integration_cluster_autodiscovery['reported_database_hostname'] = "mongohost"
    instance_integration_cluster_autodiscovery['dbm'] = True
    instance_integration_cluster_autodiscovery['slow_operations'] = {'enabled': True, 'run_sync': True}
    instance_integration_cluster_autodiscovery['database_autodiscovery']['include'] = ['integration$', 'test$']
    instance_integration_cluster_autodiscovery['operation_samples'] = {'enabled': False}
    instance_integration_cluster_autodiscovery['schemas'] = {'enabled': False}

    mongo_check = check(instance_integration_cluster_autodiscovery)
    aggregator.reset()
    with mock_pymongo("standalone"):
        run_check_once(mongo_check, dd_run_check)

    events = aggregator.get_event_platform_events("dbm-activity")
    slow_operation_payload = [event for event in events if event['dbm_type'] == 'slow_query']

    dbm_samples = aggregator.get_event_platform_events("dbm-samples")
    slow_operation_explain_plans_payload = [event for event in dbm_samples if event['dbm_type'] == 'plan']

    with open(os.path.join(HERE, "results", "slow-operations-standalone.json"), 'r') as f:
        expected_slow_operation_payload = json.load(f)
        assert slow_operation_payload == expected_slow_operation_payload

    with open(os.path.join(HERE, "results", "slow-operations-explain-plans-standalone.json"), 'r') as f:
        expected_slow_operation_explain_plans_payload = json.load(f)
        assert slow_operation_explain_plans_payload == expected_slow_operation_explain_plans_payload

    assert_metrics(
        mongo_check,
        aggregator,
        ["profiling"],
    )


@mock_now(1715911398.1112723)
@common.shard
def test_mongo_slow_operations_mongos(aggregator, instance_integration_cluster_autodiscovery, check, dd_run_check):
    instance_integration_cluster_autodiscovery['reported_database_hostname'] = "mongohost"
    instance_integration_cluster_autodiscovery['dbm'] = True
    instance_integration_cluster_autodiscovery['slow_operations'] = {'enabled': True, 'run_sync': True}
    instance_integration_cluster_autodiscovery['database_autodiscovery']['include'] = ['integration$', 'test$']
    instance_integration_cluster_autodiscovery['operation_samples'] = {'enabled': False}
    instance_integration_cluster_autodiscovery['schemas'] = {'enabled': False}

    mongo_check = check(instance_integration_cluster_autodiscovery)
    aggregator.reset()
    with mock_pymongo("mongos"):
        run_check_once(mongo_check, dd_run_check)

    events = aggregator.get_event_platform_events("dbm-activity")
    slow_operation_payload = [event for event in events if event['dbm_type'] == 'slow_query']

    dbm_samples = aggregator.get_event_platform_events("dbm-samples")
    slow_operation_explain_plans_payload = [event for event in dbm_samples if event['dbm_type'] == 'plan']

    with open(os.path.join(HERE, "results", "slow-operations-explain-plans-mongos.json"), 'r') as f:
        expected_slow_operation_explain_plans_payload = json.load(f)
        assert slow_operation_explain_plans_payload == expected_slow_operation_explain_plans_payload

    with open(os.path.join(HERE, "results", "slow-operations-mongos.json"), 'r') as f:
        expected_slow_operation_payload = json.load(f)
        assert slow_operation_payload == expected_slow_operation_payload


@common.shard
def test_mongo_slow_operations_arbiter(aggregator, instance_arbiter, check, dd_run_check):
    instance_arbiter['dbm'] = True
    instance_arbiter['cluster_name'] = 'my_cluster'
    instance_arbiter['slow_operations'] = {'enabled': True, 'run_sync': True}
    instance_arbiter['operation_samples'] = {'enabled': False}
    instance_arbiter['schemas'] = {'enabled': False}

    mongo_check = check(instance_arbiter)
    aggregator.reset()
    with mock_pymongo("replica-arbiter"):
        dd_run_check(mongo_check)

    events = aggregator.get_event_platform_events("dbm-samples")
    slow_operations = [event for event in events if event['dbm_type'] == 'slow_query']

    assert len(slow_operations) == 0


@mock_now(1715911398.1112723)
@common.standalone
def test_mongo_slow_operations_standalone_with_limit(aggregator, instance_integration_cluster, check, dd_run_check):
    instance_integration_cluster['reported_database_hostname'] = "mongohost"
    instance_integration_cluster['dbm'] = True
    instance_integration_cluster['slow_operations'] = {'enabled': True, 'run_sync': True, 'max_operations': 2}
    instance_integration_cluster['database_autodiscovery'] = {'enabled': True, 'include': ['integration$', 'test$']}
    instance_integration_cluster['operation_samples'] = {'enabled': False}

    mongo_check = check(instance_integration_cluster)
    aggregator.reset()
    with mock_pymongo("standalone"):
        run_check_once(mongo_check, dd_run_check)

    events = aggregator.get_event_platform_events("dbm-activity")
    slow_operation_payload = [event for event in events if event['dbm_type'] == 'slow_query']
    slow_operations = slow_operation_payload[0]['mongodb_slow_queries']
    assert len(slow_operations) == 2
