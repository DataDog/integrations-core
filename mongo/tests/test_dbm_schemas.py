# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os

import mock
import pytest

from . import common
from .common import HERE
from .conftest import mock_now, mock_pymongo
from .utils import run_check_once

pytestmark = [pytest.mark.usefixtures('dd_environment'), pytest.mark.integration]


@mock_now(1715911398.1112723)
@common.standalone
def test_mongo_schemas_standalone(aggregator, instance_integration_cluster_autodiscovery, check, dd_run_check):
    instance_integration_cluster_autodiscovery['reported_database_hostname'] = "mongohost"
    instance_integration_cluster_autodiscovery['dbm'] = True
    instance_integration_cluster_autodiscovery['schemas'] = {'enabled': True, 'run_sync': True}
    instance_integration_cluster_autodiscovery['database_autodiscovery']['include'] = ['integration$', 'test$']
    instance_integration_cluster_autodiscovery['operation_samples'] = {'enabled': False}
    instance_integration_cluster_autodiscovery['slow_operations'] = {'enabled': False}

    mongo_check = check(instance_integration_cluster_autodiscovery)
    aggregator.reset()
    with mock_pymongo("standalone"):
        run_check_once(mongo_check, dd_run_check)

    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    mongodb_databases = [e for e in dbm_metadata if e['kind'] == 'mongodb_databases']

    with open(os.path.join(HERE, "results", "schemas-standalone.json"), 'r') as f:
        expected_mongodb_databases = json.load(f)
        assert len(mongodb_databases) == len(expected_mongodb_databases)
        for i, db in enumerate(mongodb_databases):
            assert db == expected_mongodb_databases[i]


@mock_now(1715911398.1112723)
@common.shard
def test_mongo_schemas_mongos(aggregator, instance_integration_cluster_autodiscovery, check, dd_run_check):
    instance_integration_cluster_autodiscovery['reported_database_hostname'] = "mongohost"
    instance_integration_cluster_autodiscovery['dbm'] = True
    instance_integration_cluster_autodiscovery['schemas'] = {'enabled': True, 'run_sync': True}
    instance_integration_cluster_autodiscovery['database_autodiscovery']['include'] = ['integration$', 'test$']
    instance_integration_cluster_autodiscovery['operation_samples'] = {'enabled': False}
    instance_integration_cluster_autodiscovery['slow_operations'] = {'enabled': False}

    mongo_check = check(instance_integration_cluster_autodiscovery)
    aggregator.reset()
    with mock_pymongo("mongos"):
        run_check_once(mongo_check, dd_run_check)

    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    mongodb_databases = [e for e in dbm_metadata if e['kind'] == 'mongodb_databases']

    with open(os.path.join(HERE, "results", "schemas-mongos.json"), 'r') as f:
        expected_mongodb_databases = json.load(f)
        assert len(mongodb_databases) == len(expected_mongodb_databases)
        for i, db in enumerate(mongodb_databases):
            assert db == expected_mongodb_databases[i]


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


@mock_now(1715911398.1112723)
@common.standalone
@pytest.mark.parametrize("collect_search_indexes", [True, False])
def test_mongo_schemas_standalone_atlas(
    aggregator, instance_integration_cluster_autodiscovery, check, dd_run_check, collect_search_indexes
):
    instance_integration_cluster_autodiscovery['reported_database_hostname'] = "mongohost"
    instance_integration_cluster_autodiscovery['dbm'] = True
    instance_integration_cluster_autodiscovery['schemas'] = {
        'enabled': True,
        'run_sync': True,
        'collect_search_indexes': collect_search_indexes,
    }
    instance_integration_cluster_autodiscovery['database_autodiscovery']['include'] = ['integration$', 'test$']
    instance_integration_cluster_autodiscovery['operation_samples'] = {'enabled': False}
    instance_integration_cluster_autodiscovery['slow_operations'] = {'enabled': False}

    mongo_check = check(instance_integration_cluster_autodiscovery)
    aggregator.reset()
    with mock_pymongo("standalone"):
        with mock.patch('datadog_checks.mongo.api.MongoApi.hostname', new_callable=mock.PropertyMock) as mock_hostname:
            mock_hostname.return_value = 'atlas-hostname.mongodb.net'
            run_check_once(mongo_check, dd_run_check)

    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    mongodb_databases = [e for e in dbm_metadata if e['kind'] == 'mongodb_databases']

    expected_result = (
        "schemas-standalone-atlas-search-indexes.json" if collect_search_indexes else "schemas-standalone-atlas.json"
    )
    with open(os.path.join(HERE, "results", expected_result), 'r') as f:
        expected_mongodb_databases = json.load(f)
        assert len(mongodb_databases) == len(expected_mongodb_databases)
        for i, db in enumerate(mongodb_databases):
            assert db == expected_mongodb_databases[i]
