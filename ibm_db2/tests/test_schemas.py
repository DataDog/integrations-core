# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.ibm_db2 import IbmDb2Check

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def collect_schemas(aggregator, instance, dd_run_check, monkeypatch, collect_schemas_config):
    # Run the schema job inline so its payloads are submitted before the assertions.
    monkeypatch.setenv('DBM_THREADED_JOB_RUN_SYNC', 'true')
    instance['dbm'] = True
    instance['collect_schemas'] = collect_schemas_config
    dd_run_check(IbmDb2Check('ibm_db2', {}, [instance]))

    schemas = []
    for event in aggregator.get_event_platform_events('dbm-metadata'):
        if event['kind'] == 'ibm_db2_databases':
            for database in event['metadata']:
                assert database['name'] == 'datadog'
                schemas.extend(database['schemas'])
    return schemas


def test_schema_collection_payload(aggregator, instance, dd_run_check, monkeypatch):
    schemas = collect_schemas(
        aggregator, instance, dd_run_check, monkeypatch, {'include_schemas': ['TEST_SCHEMA', 'EMPTY_SCHEMA']}
    )

    assert {'name': 'EMPTY_SCHEMA', 'owner': 'DB2INST1', 'tables': []} in schemas
    tables = {
        table['name']: table for schema in schemas if schema['name'] == 'TEST_SCHEMA' for table in schema['tables']
    }
    assert set(tables) == {'PARENT', 'CHILD', 'EVENTS'}

    parent = tables['PARENT']
    assert parent['type'] == 'TABLE'
    assert parent['owner'] == 'DB2INST1'
    assert parent['columns'] == [
        {'name': 'ID', 'data_type': 'INTEGER', 'length': 4, 'scale': 0, 'nullable': False, 'default': None},
        {'name': 'NAME', 'data_type': 'VARCHAR', 'length': 50, 'scale': 0, 'nullable': False, 'default': "'x'"},
        {'name': 'PRICE', 'data_type': 'DECIMAL', 'length': 10, 'scale': 2, 'nullable': True, 'default': None},
    ]
    [primary_key] = parent['indexes']
    assert primary_key['is_primary'] and primary_key['is_unique']
    assert primary_key['columns'] == [{'name': 'ID', 'order': 'ASC'}]

    child_indexes = {index['name']: index for index in tables['CHILD']['indexes']}
    assert child_indexes['IDX_CHILD_PARENT'] == {
        'schema': 'TEST_SCHEMA',
        'name': 'IDX_CHILD_PARENT',
        'is_unique': False,
        'is_primary': False,
        'index_type': 'REG',
        'columns': [{'name': 'PARENT_ID', 'order': 'DESC'}],
    }
    assert tables['CHILD']['foreign_keys'] == [
        {
            'name': 'FK_PARENT',
            'columns': ['PARENT_ID'],
            'referenced_schema': 'TEST_SCHEMA',
            'referenced_table': 'PARENT',
            'referenced_columns': ['ID'],
            'delete_rule': 'CASCADE',
            'update_rule': 'NO ACTION',
        }
    ]

    assert tables['EVENTS']['partition_key'] == ['TS']
    assert tables['EVENTS']['num_partitions'] == 2
    assert 'partition_key' not in parent


@pytest.mark.parametrize(
    'collect_schemas_config, expected_tables',
    [
        pytest.param({'exclude_tables': ['CH.*']}, {'PARENT', 'EVENTS'}, id='exclude_tables'),
        pytest.param({'include_tables': ['PARENT']}, {'PARENT'}, id='include_tables'),
        pytest.param({'max_tables': 1}, {'CHILD'}, id='max_tables'),
        pytest.param({'enabled': False}, set(), id='disabled'),
    ],
)
def test_schema_collection_filters(
    aggregator, instance, dd_run_check, monkeypatch, collect_schemas_config, expected_tables
):
    collect_schemas_config = {'include_schemas': ['TEST_SCHEMA'], **collect_schemas_config}
    schemas = collect_schemas(aggregator, instance, dd_run_check, monkeypatch, collect_schemas_config)

    assert {table['name'] for schema in schemas for table in schema['tables']} == expected_tables


def test_schema_collection_max_columns(aggregator, instance, dd_run_check, monkeypatch):
    schemas = collect_schemas(
        aggregator,
        instance,
        dd_run_check,
        monkeypatch,
        {'include_schemas': ['TEST_SCHEMA'], 'include_tables': ['PARENT'], 'max_columns': 2},
    )

    [table] = [table for schema in schemas for table in schema['tables']]
    assert [column['name'] for column in table['columns']] == ['ID', 'NAME']
