# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os

import pytest

from . import common
from .common import HERE
from .conftest import mock_now, mock_pymongo
from .utils import run_check_once

pytestmark = [pytest.mark.usefixtures('dd_environment'), pytest.mark.integration]


@mock_now(1715911398.1112723)
@common.standalone
def test_mongo_operation_samples_standalone(aggregator, instance_integration_cluster, check, dd_run_check):
    instance_integration_cluster['dbm'] = True
    instance_integration_cluster['operation_samples'] = {'enabled': True, 'run_sync': True}

    mongo_check = check(instance_integration_cluster)
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
def test_mongo_operation_samples_mongos(aggregator, instance_integration_cluster, check, dd_run_check):
    instance_integration_cluster['dbm'] = True
    instance_integration_cluster['operation_samples'] = {'enabled': True, 'run_sync': True}

    mongo_check = check(instance_integration_cluster)
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

    mongo_check = check(instance_arbiter)
    aggregator.reset()
    with mock_pymongo("replica-arbiter"):
        dd_run_check(mongo_check)

    dbm_samples = aggregator.get_event_platform_events("dbm-samples")
    dbm_activities = aggregator.get_event_platform_events("dbm-activity")

    assert len(dbm_samples) == 0
    assert len(dbm_activities) == 0
