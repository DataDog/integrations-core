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
def test_mongo_schemas_standalone(aggregator, instance_integration_cluster, check, dd_run_check):
    instance_integration_cluster['reported_database_hostname'] = "mongohost"
    instance_integration_cluster['dbm'] = True
    instance_integration_cluster['schemas'] = {'enabled': True, 'run_sync': True}
    instance_integration_cluster['database_autodiscovery'] = {'enabled': True, 'include': ['integration$', 'test$']}
    instance_integration_cluster['operation_samples'] = {'enabled': False}
    instance_integration_cluster['slow_operations'] = {'enabled': False}

    mongo_check = check(instance_integration_cluster)
    aggregator.reset()
    with mock_pymongo("standalone"):
        run_check_once(mongo_check, dd_run_check)

    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    mongodb_databases = next((e for e in dbm_metadata if e['kind'] == 'mongodb_databases'), None)

    with open(os.path.join(HERE, "results", "schemas-standalone.json"), 'r') as f:
        expected_mongodb_databases = json.load(f)
        print(json.dumps(mongodb_databases))
        assert mongodb_databases == expected_mongodb_databases


@mock_now(1715911398.1112723)
@common.shard
def test_mongo_schemas_mongos(aggregator, instance_integration_cluster, check, dd_run_check):
    instance_integration_cluster['reported_database_hostname'] = "mongohost"
    instance_integration_cluster['dbm'] = True
    instance_integration_cluster['schemas'] = {'enabled': True, 'run_sync': True}
    instance_integration_cluster['database_autodiscovery'] = {'enabled': True, 'include': ['integration$', 'test$']}
    instance_integration_cluster['operation_samples'] = {'enabled': False}
    instance_integration_cluster['slow_operations'] = {'enabled': False}

    mongo_check = check(instance_integration_cluster)
    aggregator.reset()
    with mock_pymongo("mongos"):
        run_check_once(mongo_check, dd_run_check)

    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    mongodb_databases = next((e for e in dbm_metadata if e['kind'] == 'mongodb_databases'), None)

    with open(os.path.join(HERE, "results", "schemas-mongos.json"), 'r') as f:
        expected_mongodb_databases = json.load(f)
        print(json.dumps(mongodb_databases))
        assert mongodb_databases == expected_mongodb_databases


@common.shard
def test_mongo_schemas_arbiter(aggregator, instance_arbiter, check, dd_run_check):
    instance_arbiter['dbm'] = True
    instance_arbiter['cluster_name'] = 'my_cluster'
    instance_arbiter['schemas'] = {'enabled': True, 'run_sync': True}
    instance_arbiter['operation_samples'] = {'enabled': False}
    instance_arbiter['slow_operations'] = {'enabled': False}

    mongo_check = check(instance_arbiter)
    aggregator.reset()
    with mock_pymongo("replica-arbiter"):
        dd_run_check(mongo_check)

    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    mongodb_databases = next((e for e in dbm_metadata if e['kind'] == 'mongodb_databases'), None)

    assert mongodb_databases is None
