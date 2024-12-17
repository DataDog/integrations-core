# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os

import mock
import pytest
from pymongo.errors import NotPrimaryError

from . import common
from .common import HERE
from .conftest import mock_now, mock_pymongo
from .utils import run_check_once

pytestmark = [pytest.mark.usefixtures('dd_environment'), pytest.mark.integration]


@mock_now(1715911398.1112723)
@common.standalone
def test_mongo_operation_samples_standalone(
    aggregator, instance_integration_cluster_autodiscovery, check, dd_run_check
):
    instance_integration_cluster_autodiscovery['dbm'] = True
    instance_integration_cluster_autodiscovery['operation_samples'] = {'enabled': True, 'run_sync': True}
    instance_integration_cluster_autodiscovery['slow_operations'] = {'enabled': False}
    instance_integration_cluster_autodiscovery['schemas'] = {'enabled': False}

    mongo_check = check(instance_integration_cluster_autodiscovery)
    with mock_pymongo("standalone"):
        aggregator.reset()
        run_check_once(mongo_check, dd_run_check)

    # we will not assert the metrics, as they are already tested in test_integration.py
    # we will only assert the operation sample and activity events
    dbm_activities = aggregator.get_event_platform_events("dbm-activity")
    dbm_samples = aggregator.get_event_platform_events("dbm-samples")

    activity_samples = [event for event in dbm_activities if event['dbm_type'] == 'activity']
    plan_samples = [event for event in dbm_samples if event['dbm_type'] == 'plan']

    # assert samples
    with open(os.path.join(HERE, "results", "operation-samples-standalone.json"), 'r') as f:
        expected_samples = json.load(f)
        assert len(plan_samples) == len(expected_samples)
        for i, sample in enumerate(plan_samples):
            assert sample == expected_samples[i]

    # assert activities
    with open(os.path.join(HERE, "results", "operation-activities-standalone.json"), 'r') as f:
        expected_activities = json.load(f)
        assert len(activity_samples) == len(expected_activities)
        for i, activity in enumerate(activity_samples):
            # do not assert timestamp
            assert activity == expected_activities[i]


@mock_now(1715911398.11127223)
@common.shard
def test_mongo_operation_samples_mongos(aggregator, instance_integration_cluster_autodiscovery, check, dd_run_check):
    instance_integration_cluster_autodiscovery['dbm'] = True
    instance_integration_cluster_autodiscovery['operation_samples'] = {'enabled': True, 'run_sync': True}
    instance_integration_cluster_autodiscovery['slow_operations'] = {'enabled': False}
    instance_integration_cluster_autodiscovery['schemas'] = {'enabled': False}

    mongo_check = check(instance_integration_cluster_autodiscovery)
    aggregator.reset()
    with mock_pymongo("mongos"):
        run_check_once(mongo_check, dd_run_check)

    dbm_activities = aggregator.get_event_platform_events("dbm-activity")
    dbm_samples = aggregator.get_event_platform_events("dbm-samples")

    activity_samples = [event for event in dbm_activities if event['dbm_type'] == 'activity']
    plan_samples = [event for event in dbm_samples if event['dbm_type'] == 'plan']

    with open(os.path.join(HERE, "results", "operation-samples-mongos.json"), 'r') as f:
        expected_samples = json.load(f)
        assert len(plan_samples) == len(expected_samples)
        for i, sample in enumerate(plan_samples):
            assert sample == expected_samples[i]

    # assert activities
    with open(os.path.join(HERE, "results", "operation-activities-mongos.json"), 'r') as f:
        expected_activities = json.load(f)
        assert len(activity_samples) == len(expected_activities)
        for i, activity in enumerate(activity_samples):
            assert activity == expected_activities[i]


@common.shard
def test_mongo_operation_samples_arbiter(aggregator, instance_arbiter, check, dd_run_check):
    instance_arbiter['dbm'] = True
    instance_arbiter['cluster_name'] = 'my_cluster'
    instance_arbiter['operation_samples'] = {'enabled': True, 'run_sync': True}
    instance_arbiter['slow_operations'] = {'enabled': False}
    instance_arbiter['schemas'] = {'enabled': False}

    mongo_check = check(instance_arbiter)
    aggregator.reset()
    with mock_pymongo("replica-arbiter"):
        dd_run_check(mongo_check)

    dbm_samples = aggregator.get_event_platform_events("dbm-samples")
    dbm_activities = aggregator.get_event_platform_events("dbm-activity")

    assert len(dbm_samples) == 0
    assert len(dbm_activities) == 0


@mock_now(1715911398.1112723)
@common.shard
def test_mongo_operation_samples_not_primary(
    aggregator, instance_integration_cluster_autodiscovery, check, dd_run_check
):
    instance_integration_cluster_autodiscovery['dbm'] = True
    instance_integration_cluster_autodiscovery['operation_samples'] = {'enabled': True, 'run_sync': True}
    instance_integration_cluster_autodiscovery['slow_operations'] = {'enabled': False}
    instance_integration_cluster_autodiscovery['schemas'] = {'enabled': False}

    mongo_check = check(instance_integration_cluster_autodiscovery)
    with mock_pymongo("standalone"):
        with mock.patch(
            'datadog_checks.mongo.api.MongoApi.current_op', new_callable=mock.PropertyMock
        ) as mock_current_op:
            mock_current_op.side_effect = NotPrimaryError("node is recovering")
            aggregator.reset()
            run_check_once(mongo_check, dd_run_check)

    dbm_activities = aggregator.get_event_platform_events("dbm-activity")
    activity_samples = [event for event in dbm_activities if event['dbm_type'] == 'activity']
    assert activity_samples is not None
    assert len(activity_samples[0]['mongodb_activity']) == 0

    aggregator.reset()
    mongo_check.deployment_type.replset_state = 3
    run_check_once(mongo_check, dd_run_check)
    dbm_activities = aggregator.get_event_platform_events("dbm-activity")
    activity_samples = [event for event in dbm_activities if event['dbm_type'] == 'activity']
    assert len(activity_samples) == 0
