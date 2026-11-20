# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from collections.abc import Callable

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.ibm_db2 import IbmDb2Check

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def collect_schemas(aggregator, instance, dd_run_check, collect_schemas_config):
    instance['dbm'] = True
    instance['collect_schemas'] = collect_schemas_config
    check = IbmDb2Check('ibm_db2', {}, [instance])
    # Run the schema job inline so its payloads are submitted before the assertions.
    check._schema_collection._run_sync = True
    dd_run_check(check)

    schemas = []
    for event in aggregator.get_event_platform_events('dbm-metadata'):
        if event['kind'] == 'ibm_db2_databases':
            for database in event['metadata']:
                assert database['name'] == 'datadog'
                schemas.extend(database['schemas'])
    return schemas


def test_schema_collection_payload(aggregator, instance, dd_run_check):
    schemas = collect_schemas(aggregator, instance, dd_run_check, {'include_schemas': ['TEST_SCHEMA', 'EMPTY_SCHEMA']})

    assert {'name': 'EMPTY_SCHEMA', 'owner': 'DB2INST1', 'tables': []} in schemas
    tables = {
        table['name']: table for schema in schemas if schema['name'] == 'TEST_SCHEMA' for table in schema['tables']
    }
    assert set(tables) == {'PARENT', 'CHILD', 'EVENTS'}

    parent = tables['PARENT']
    assert parent['type'] == 'TABLE'
    assert parent['owner'] == 'DB2INST1'
    assert parent['columns'] == [
        {'name': 'ID', 'data_type': 'INTEGER', 'length': 4, 'scale': 0, 'is_nullable': False, 'default': None},
        {'name': 'NAME', 'data_type': 'VARCHAR', 'length': 50, 'scale': 0, 'is_nullable': False, 'default': "'x'"},
        {'name': 'PRICE', 'data_type': 'DECIMAL', 'length': 10, 'scale': 2, 'is_nullable': True, 'default': None},
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
    ],
)
def test_schema_collection_filters(aggregator, instance, dd_run_check, collect_schemas_config, expected_tables):
    collect_schemas_config = {'include_schemas': ['TEST_SCHEMA'], **collect_schemas_config}
    schemas = collect_schemas(aggregator, instance, dd_run_check, collect_schemas_config)

    assert {table['name'] for schema in schemas for table in schema['tables']} == expected_tables


def test_schema_collection_max_columns(aggregator, instance, dd_run_check):
    schemas = collect_schemas(
        aggregator,
        instance,
        dd_run_check,
        {'include_schemas': ['TEST_SCHEMA'], 'include_tables': ['PARENT'], 'max_columns': 2},
    )

    [table] = [table for schema in schemas for table in schema['tables']]
    assert [column['name'] for column in table['columns']] == ['ID', 'NAME']


@pytest.mark.parametrize('include_tables, expected_table', [([], 'CHILD'), (['PARENT'], 'PARENT')])
def test_schema_collection_table_budget(
    aggregator: AggregatorStub,
    instance: dict,
    dd_run_check: Callable,
    include_tables: list[str],
    expected_table: str,
):
    """Empty and filtered schemas must not displace qualifying tables from a limited snapshot."""
    schemas = collect_schemas(
        aggregator,
        instance,
        dd_run_check,
        {
            'include_schemas': ['EMPTY_SCHEMA', 'FILTERED_SCHEMA', 'TEST_SCHEMA'],
            'exclude_tables': ['HIDDEN'],
            'include_tables': include_tables,
            'max_tables': 1,
        },
    )
    assert {'name': 'EMPTY_SCHEMA', 'owner': 'DB2INST1', 'tables': []} in schemas
    assert {'name': 'FILTERED_SCHEMA', 'owner': 'DB2INST1', 'tables': []} in schemas
    assert [(schema['name'], table['name']) for schema in schemas for table in schema['tables']] == [
        ('TEST_SCHEMA', expected_table)
    ]


def test_schema_collection_disabled(aggregator: AggregatorStub, instance: dict, dd_run_check: Callable):
    """Disabling schema collection must suppress even empty metadata snapshots."""
    collect_schemas(aggregator, instance, dd_run_check, {'enabled': False})
    assert not any(
        event['kind'] == 'ibm_db2_databases' for event in aggregator.get_event_platform_events('dbm-metadata')
    )
