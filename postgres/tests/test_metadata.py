# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from concurrent.futures.thread import ThreadPoolExecutor
from typing import List

import pytest

from datadog_checks.base.utils.db.utils import DBMAsyncJob

from .common import POSTGRES_VERSION
from .utils import run_one_check

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


@pytest.fixture
def dbm_instance(pg_instance):
    pg_instance['dbm'] = True
    pg_instance['min_collection_interval'] = 0.1
    pg_instance['query_samples'] = {'enabled': False}
    pg_instance['query_activity'] = {'enabled': False}
    pg_instance['query_metrics'] = {'enabled': False}
    pg_instance['collect_settings'] = {'enabled': True, 'run_sync': True, 'collection_interval': 0.1}
    return pg_instance


@pytest.fixture(autouse=True)
def stop_orphaned_threads():
    # make sure we shut down any orphaned threads and create a new Executor for each test
    DBMAsyncJob.executor.shutdown(wait=True)
    DBMAsyncJob.executor = ThreadPoolExecutor()


def test_collect_extensions(integration_check, dbm_instance, aggregator):
    check = integration_check(dbm_instance)
    check.check(dbm_instance)
    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    event = next((e for e in dbm_metadata if e['kind'] == 'pg_extension'), None)
    assert event is not None
    assert event['host'] == "stubbed.hostname"
    assert event['dbms'] == "postgres"
    assert event['kind'] == "pg_extension"
    assert len(event["metadata"]) > 0
    assert set(event["metadata"][0].keys()) == {'id', 'name', 'owner', 'relocatable', 'schema_name', 'version'}
    assert type(event["metadata"][0]["id"]) is str
    assert next((k for k in event['metadata'] if k['name'].startswith('plpgsql')), None) is not None


def test_collect_metadata(integration_check, dbm_instance, aggregator):
    dbm_instance["collect_settings"]['ignored_settings_patterns'] = ['max_wal%']
    check = integration_check(dbm_instance)
    check.check(dbm_instance)
    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    event = next((e for e in dbm_metadata if e['kind'] == 'pg_settings'), None)
    assert event is not None
    assert event['host'] == "stubbed.hostname"
    assert event['dbms'] == "postgres"
    assert event['kind'] == "pg_settings"
    assert len(event["metadata"]) > 0
    assert set(event["metadata"][0].keys()) == {'name', 'setting', 'source', 'sourcefile', 'pending_restart'}
    assert all(not k['name'].startswith('max_wal') for k in event['metadata'])
    assert next((k for k in event['metadata'] if k['name'].startswith('pg_trgm')), None) is not None
    statement_timeout_setting = next((k for k in event['metadata'] if k['name'] == 'statement_timeout'), None)
    assert statement_timeout_setting is not None
    # statement_timeout should be server level setting not session level
    assert statement_timeout_setting['setting'] == '10000'


@pytest.mark.parametrize(
    "use_default_ignore_schemas_owned_by",
    [
        pytest.param(True, id="default_ignore_schemas_owned_by"),
        pytest.param(False, id="custom_ignore_schemas_owned_by"),
    ],
)
def test_collect_schemas(integration_check, dbm_instance, aggregator, use_default_ignore_schemas_owned_by):
    dbm_instance["collect_schemas"] = {'enabled': True, 'collection_interval': 600}
    dbm_instance['relations'] = []
    dbm_instance["database_autodiscovery"] = {"enabled": True, "include": ["datadog"]}
    del dbm_instance['dbname']
    if not use_default_ignore_schemas_owned_by:
        dbm_instance["ignore_schemas_owned_by"] = ['rds_superuser']
    check = integration_check(dbm_instance)
    run_one_check(check, dbm_instance)
    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")

    # check that all expected tables are present
    tables_set = {
        'persons',
        "personsdup1",
        "personsdup2",
        "personsdup3",
        "personsdup4",
        "personsdup5",
        "personsdup6",
        "personsdup7",
        "personsdup8",
        "personsdup9",
        "personsdup10",
        "personsdup11",
        "personsdup12",
        "pgtable",
        "pg_newtable",
        "cities",
        "sample_foreign_d73a8c",
    }
    # if version isn't 9 or 10, check that partition master is in tables
    if float(POSTGRES_VERSION) >= 11:
        tables_set.update({'test_part', 'test_part_no_children', 'test_part_no_activity'})
    tables_not_reported_set = {'test_part1', 'test_part2'}

    tables_got = []

    schemas_want = {
        'public',
        'public2',
        'datadog',
        'hstore',
    }

    if not use_default_ignore_schemas_owned_by:
        schemas_want.add('rdsadmin_test')
        tables_set.add('rds_admin_misc')

    schemas_got = set()

    collection_started_at = None
    schema_events = [e for e in dbm_metadata if e['kind'] == 'pg_databases']
    print(schema_events)
    for i, schema_event in enumerate(schema_events):
        for mi, _ in enumerate(schema_event['metadata']):
            assert schema_event.get("timestamp") is not None
            if collection_started_at is None:
                collection_started_at = schema_event["collection_started_at"]
            assert schema_event["collection_started_at"] == collection_started_at

            if i == len(schema_events) - 1:
                assert schema_event["collection_payloads_count"] == len(schema_events)
            else:
                assert "collection_payloads_count" not in schema_event

            # there should only be one database, datadog_test
            database_metadata = schema_event['metadata']
            assert 'datadog_test' == database_metadata[mi]['name']

            # there should only two schemas, 'public' and 'datadog'. datadog is empty
            schema = database_metadata[mi]['schemas'][0]
            schema_name = schema['name']
            assert schema['owner'] == 'pg_database_owner' if schema_name == 'public' else 'postgres'
            assert schema_name in ['public', 'public2', 'datadog', 'rdsadmin_test', 'hstore']
            schemas_got.add(schema_name)
            if schema_name in ['public', 'rdsadmin_test']:
                for table in schema['tables']:
                    tables_got.append(table['name'])

                    # make some assertions on fields
                    if table['name'] == "persons":
                        # check that foreign keys, indexes get reported
                        keys = list(table.keys())
                        assert_fields(keys, ["foreign_keys", "columns", "id", "name"])
                        # The toast table doesn't seem to be created in the C locale
                        # if POSTGRES_LOCALE != 'C':
                        #     assert_fields(keys, ["toast_table"])
                        assert_fields(list(table['foreign_keys'][0].keys()), ['name', 'definition'])
                        assert_fields(
                            list(table['columns'][0].keys()),
                            [
                                'name',
                                'nullable',
                                'data_type',
                                'default',
                            ],
                        )
                    if table['name'] == "cities":
                        keys = list(table.keys())
                        assert_fields(keys, ["indexes", "columns", "id", "name"])
                        # if POSTGRES_LOCALE != 'C':
                        #     assert_fields(keys, ["toast_table"])
                        assert len(table['indexes']) == 1
                        assert_fields(
                            list(table['indexes'][0].keys()),
                            [
                                'name',
                                'definition',
                                'is_unique',
                                'is_exclusion',
                                'is_immediate',
                                'is_clustered',
                                'is_valid',
                                'is_checkxmin',
                                'is_ready',
                                'is_live',
                                'is_replident',
                                'is_partial',
                            ],
                        )
                    if float(POSTGRES_VERSION) >= 11:
                        if table['name'] in ('test_part', 'test_part_no_activity'):
                            keys = list(table.keys())
                            assert_fields(keys, ["indexes", "num_partitions", "partition_key"])
                            assert table['num_partitions'] == 2
                        elif table['name'] == 'test_part_no_children':
                            keys = list(table.keys())
                            assert_fields(keys, ["partition_key"])

    assert schemas_want == schemas_got
    assert_fields(tables_got, tables_set)
    assert_not_fields(tables_got, tables_not_reported_set)


def test_collect_schemas_filters(integration_check, dbm_instance, aggregator):
    test_cases = [
        [
            {'include_databases': ['.*'], 'include_schemas': ['public'], 'include_tables': ['.*']},
            [
                "persons",
                "personsdup1",
                "personsdup2",
                "personsdup3",
                "personsdup4",
                "personsdup5",
                "personsdup6",
                "personsdup7",
                "personsdup8",
                "personsdup9",
                "personsdup10",
                "personsdup11",
                "personsdup12",
                "pgtable",
                "pg_newtable",
                "cities",
            ],
            [],
        ],
        [
            {'exclude_tables': ['person.*']},
            [
                "pgtable",
                "pg_newtable",
                "cities",
            ],
            [
                "persons",
                "personsdup1",
                "personsdup2",
                "personsdup3",
                "personsdup4",
                "personsdup5",
                "personsdup6",
                "personsdup7",
                "personsdup8",
                "personsdup9",
                "personsdup10",
                "personsdup11",
                "personsdup12",
            ],
        ],
        [
            {'include_tables': ['person.*'], 'exclude_tables': ['person.*']},
            [],
            [
                "persons",
                "personsdup1",
                "personsdup2",
                "personsdup3",
                "personsdup4",
                "personsdup5",
                "personsdup6",
                "personsdup7",
                "personsdup8",
                "personsdup9",
                "personsdup10",
                "personsdup11",
                "personsdup12",
            ],
        ],
        [
            {'include_tables': ['person.*', "cities"]},
            [
                "persons",
                "personsdup1",
                "personsdup2",
                "personsdup3",
                "personsdup4",
                "personsdup5",
                "personsdup6",
                "personsdup7",
                "personsdup8",
                "personsdup9",
                "personsdup10",
                "personsdup11",
                "personsdup12",
                "cities",
            ],
            [
                "pgtable",
                "pg_newtable",
            ],
        ],
        [
            {'exclude_tables': ['person.*', "cities"]},
            [
                "pgtable",
                "pg_newtable",
            ],
            [
                "persons",
                "personsdup1",
                "personsdup2",
                "personsdup3",
                "personsdup4",
                "personsdup5",
                "personsdup6",
                "personsdup7",
                "personsdup8",
                "personsdup9",
                "personsdup10",
                "personsdup11",
                "personsdup12",
                "cities",
            ],
        ],
        [
            {'include_tables': ['person.*1', "cities"], 'exclude_tables': ['person.*2', "pg.*"]},
            [
                "cities",
                "personsdup1",
                "personsdup10",
                "personsdup11",
            ],
            [
                "persons",
                "personsdup2",
                "personsdup3",
                "personsdup4",
                "personsdup5",
                "personsdup6",
                "personsdup7",
                "personsdup8",
                "personsdup9",
                "personsdup12",
                "pgtable",
                "pg_newtable",
            ],
        ],
    ]

    del dbm_instance['dbname']
    dbm_instance["database_autodiscovery"] = {"enabled": True, "include": ["datadog"]}
    dbm_instance['relations'] = []

    for tc in test_cases:
        dbm_instance["collect_schemas"] = {'enabled': True, 'run_sync': True, **tc[0]}
        check = integration_check(dbm_instance)
        run_one_check(check, dbm_instance)
        dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")

        tables_got = []

        for schema_event in (e for e in dbm_metadata if e['kind'] == 'pg_databases'):
            for mi, _ in enumerate(schema_event['metadata']):
                database_metadata = schema_event['metadata'][mi]
                schema = database_metadata['schemas'][0]
                schema_name = schema['name']
                assert schema_name in ['public', 'public2', 'datadog', 'rdsadmin_test', 'hstore']
                if schema_name == 'public':
                    for table in schema['tables']:
                        if 'name' in table:
                            tables_got.append(table['name'])
                        else:
                            print(table)

        assert_fields(tables_got, tc[1])
        assert_not_fields(tables_got, tc[2])
        aggregator.reset()


def test_collect_schemas_max_tables(integration_check, dbm_instance, aggregator):
    dbm_instance["collect_schemas"] = {'enabled': True, 'collection_interval': 0.5, 'max_tables': 1}
    dbm_instance['relations'] = []
    dbm_instance["database_autodiscovery"] = {"enabled": True, "include": ["datadog"]}
    del dbm_instance['dbname']
    check = integration_check(dbm_instance)
    run_one_check(check, dbm_instance)
    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")

    for schema_event in (e for e in dbm_metadata if e['kind'] == 'pg_databases'):
        database_metadata = schema_event['metadata']
        assert len(database_metadata[0]['schemas'][0]['tables']) <= 1

    # Rerun check with relations enabled
    dbm_instance['relations'] = [{'relation_regex': '.*'}]
    check = integration_check(dbm_instance)
    run_one_check(check, dbm_instance)
    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")

    for schema_event in (e for e in dbm_metadata if e['kind'] == 'pg_databases'):
        database_metadata = schema_event['metadata']
        assert len(database_metadata[0]['schemas'][0]['tables']) <= 1


def test_collect_schemas_multiple_payloads(integration_check, dbm_instance, aggregator):
    dbm_instance["collect_schemas"] = {'enabled': True, 'collection_interval': 0.5}
    dbm_instance['relations'] = []
    dbm_instance["database_autodiscovery"] = {"enabled": True, "include": ["datadog"]}
    del dbm_instance['dbname']
    check = integration_check(dbm_instance)
    check.metadata_samples._schema_collector._config.payload_chunk_size = 1
    run_one_check(check, dbm_instance)

    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    schema_events = [e for e in dbm_metadata if e['kind'] == 'pg_databases']
    assert len(schema_events) > 1
    # Check that all the payloads have the same collection_started_at
    collection_started_at = schema_events[0]['collection_started_at']
    for schema_event in schema_events:
        assert schema_event['collection_started_at'] == collection_started_at
    # Check that only the last payload has the collection_payloads_count
    # and that the count matches the number of payloads
    collection_payloads_count = schema_events[-1]['collection_payloads_count']
    assert collection_payloads_count == len(schema_events)
    for schema_event in schema_events[:-1]:
        assert 'collection_payloads_count' not in schema_event


def assert_fields(keys: List[str], fields: List[str]):
    for field in fields:
        assert field in keys


def assert_not_fields(keys: List[str], fields: List[str]):
    for field in fields:
        assert field not in keys
