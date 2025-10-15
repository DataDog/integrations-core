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


@pytest.mark.unit
def test_mongo_schemas_config_deprecations(instance_integration_cluster_autodiscovery, check):
    instance_integration_cluster_autodiscovery['dbm'] = True

    instance_integration_cluster_autodiscovery['schemas'] = {'enabled': True}
    mongo_check = check(instance_integration_cluster_autodiscovery)
    assert mongo_check._config.schemas['enabled'] is True

    instance_integration_cluster_autodiscovery.pop('schemas')
    instance_integration_cluster_autodiscovery['collect_schemas'] = {'enabled': True}
    mongo_check = check(instance_integration_cluster_autodiscovery)
    assert mongo_check._config.schemas['enabled'] is True


@pytest.mark.unit
def test_mongo_schemas_max_fields_cap(instance_integration_cluster_autodiscovery, check):
    instance_integration_cluster_autodiscovery['dbm'] = True
    instance_integration_cluster_autodiscovery['schemas'] = {
        'enabled': True,
        'run_sync': True,
        'sample_size': 2,
        'max_fields_per_collection': 2,
    }
    instance_integration_cluster_autodiscovery['operation_samples'] = {'enabled': False}
    instance_integration_cluster_autodiscovery['slow_operations'] = {'enabled': False}

    mongo_check = check(instance_integration_cluster_autodiscovery)
    schema_job = mongo_check._schemas

    sample_docs = [
        {'field_a': 1, 'field_b': 'a', 'field_c': 'c'},
        {'field_a': 2, 'field_d': {'nested': 'value'}},
    ]

    mock_api = mock.MagicMock()
    mock_api.sample.return_value = sample_docs
    schema_job._check.api_client = mock_api

    schema = schema_job._discover_collection_schema('db', 'collection')
    assert len(schema) == 2
    assert schema[0]['name'] == 'field_a'
    assert {entry['name'] for entry in schema} == {'field_a', 'field_b'}
    mock_api.sample.assert_called_once_with('db', 'collection', 2)


@pytest.mark.unit
def test_mongo_schemas_max_fields_cap_disabled(instance_integration_cluster_autodiscovery, check):
    instance_integration_cluster_autodiscovery['dbm'] = True
    instance_integration_cluster_autodiscovery['schemas'] = {
        'enabled': True,
        'run_sync': True,
        'sample_size': 2,
        'max_fields_per_collection': 0,
    }
    instance_integration_cluster_autodiscovery['operation_samples'] = {'enabled': False}
    instance_integration_cluster_autodiscovery['slow_operations'] = {'enabled': False}

    mongo_check = check(instance_integration_cluster_autodiscovery)
    schema_job = mongo_check._schemas

    sample_docs = [
        {'field_a': 1, 'field_b': 'a', 'field_c': 'c'},
        {'field_a': 2, 'field_d': {'nested': 'value'}},
    ]

    mock_api = mock.MagicMock()
    mock_api.sample.return_value = sample_docs
    schema_job._check.api_client = mock_api

    schema = schema_job._discover_collection_schema('db', 'collection')
    assert len(schema) == 5
    assert {entry['name'] for entry in schema} == {
        'field_a',
        'field_b',
        'field_c',
        'field_d',
        'field_d.nested',
    }
