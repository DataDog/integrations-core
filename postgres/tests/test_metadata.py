# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from concurrent.futures.thread import ThreadPoolExecutor

import pytest

from datadog_checks.base.utils.db.utils import DBMAsyncJob

from .utils import run_one_check
from .common import POSTGRES_VERSION

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


@pytest.fixture
def dbm_instance(pg_instance):
    pg_instance['dbm'] = True
    pg_instance['min_collection_interval'] = 0.1
    pg_instance['query_samples'] = {'enabled': False}
    pg_instance['query_activity'] = {'enabled': False}
    pg_instance['query_metrics'] = {'enabled': False}
    pg_instance['collect_resources'] = {'enabled': True, 'run_sync': True, 'collection_interval': 0.1}
    pg_instance['collect_settings'] = {'enabled': True, 'run_sync': True, 'collection_interval': 0.1}
    return pg_instance


@pytest.fixture(autouse=True)
def stop_orphaned_threads():
    # make sure we shut down any orphaned threads and create a new Executor for each test
    DBMAsyncJob.executor.shutdown(wait=True)
    DBMAsyncJob.executor = ThreadPoolExecutor()


def test_collect_metadata(integration_check, dbm_instance, aggregator):
    check = integration_check(dbm_instance)
    check.check(dbm_instance)
    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    event = dbm_metadata[0]
    assert event['host'] == "stubbed.hostname"
    assert event['dbms'] == "postgres"
    assert event['kind'] == "pg_settings"
    assert len(event["metadata"]) > 0


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_collect_schemas(integration_check, dbm_instance, aggregator):
    dbm_instance["collect_schemas"] = {'enabled': True, 'collection_interval': 0.5}
    dbm_instance['relations'] = [{'relation_regex': ".*"}]
    dbm_instance["database_autodiscovery"] = {"enabled": True, "include": ["datadog"]}
    del dbm_instance['dbname']
    check = integration_check(dbm_instance)
    run_one_check(check, dbm_instance)
    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    schema_event = None
    for event in dbm_metadata:
        if event['kind'] == "pg_databases":
            schema_event = event
    assert schema_event is not None
    assert schema_event['host'] == "stubbed.hostname"
    assert schema_event['dbms'] == "postgres"
    assert schema_event['kind'] == "pg_databases"
    assert len(event["metadata"]) > 0


def test_get_table_info_relations_enabled(integration_check, dbm_instance, aggregator):
    dbm_instance["collect_schemas"] = {'enabled': True, 'collection_interval': 0.5}
    dbm_instance['relations'] = [{'relation_regex': ".*"}]
    dbm_instance["database_autodiscovery"] = {"enabled": True, "include": ["datadog"]}
    del dbm_instance['dbname']
    check = integration_check(dbm_instance)
    run_one_check(check, dbm_instance)
    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    schema_event = None
    for event in dbm_metadata:
        if event['kind'] == "pg_databases":
            schema_event = event

    # there should only be one database, datadog_test
    database_metadata = schema_event['metadata']
    assert len(database_metadata) == 1
    assert 'datadog_test' == database_metadata[0]['name']

    # there should only two schemas, 'public' and 'datadog'. datadog is empty
    schema_metadata_public = database_metadata[0]['schemas'][0]
    schema_metadata_datadog = database_metadata[0]['schemas'][1]
    assert 'public' == schema_metadata_public['name']
    assert 'datadog' == schema_metadata_datadog['name']

    # check that all expected tables are present
    tables_set = {'persons', "personsdup1", "personsdup2", "pgtable", "pg_newtable", "cities"}
    # if version isn't 9 or 10, check that partition master is in tables
    if not (POSTGRES_VERSION.split('.')[0] == 9) and  not (POSTGRES_VERSION.split('.')[0] == 10):
        tables_set.update({'test_part'})
    tables_not_reported_set = {'test_part1', 'test_part2'}

    tables_got = []
    for table in schema_metadata_public['tables']:
        tables_got.append(table['name'])


    for table in tables_got:
        assert table in tables_set
        assert table not in tables_not_reported_set

    assert None is not None


    
        

