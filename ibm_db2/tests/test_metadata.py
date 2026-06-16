# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

import mock
import pytest

from datadog_checks.ibm_db2 import IbmDb2Check
from datadog_checks.ibm_db2.schemas import _render_data_type

pytestmark = pytest.mark.unit


def _dbm_check(instance: dict[str, Any]) -> IbmDb2Check:
    instance.update(
        {
            'dbm': True,
            'collect_settings': {'run_sync': True, 'collection_interval': 0.1},
            'reported_hostname': 'db2.example.com',
            'database_identifier': {'template': '$resolved_hostname:$db'},
        }
    )
    check = IbmDb2Check('ibm_db2', {}, [instance])
    check._dbms_version = '12.01.0400'
    return check


def test_db2_settings_payload(instance: dict[str, Any], aggregator: Any) -> None:
    check = _dbm_check(instance)
    check.connection.query = mock.Mock(
        return_value=(
            [
                {
                    'name': 'mon_act_metrics',
                    'value': 'BASE',
                    'value_flags': '',
                    'deferred_value': 'BASE',
                    'deferred_value_flags': '',
                    'datatype': 'VARCHAR',
                    'member': 0,
                    'config_scope': 'db',
                },
                {
                    'name': 'diaglevel',
                    'value': '3',
                    'value_flags': '',
                    'deferred_value': '4',
                    'deferred_value_flags': '',
                    'datatype': 'INTEGER',
                    'member': None,
                    'config_scope': 'dbm',
                },
            ],
            [],
        )
    )

    check.dbm_metadata.run_job()

    event = aggregator.get_event_platform_events('dbm-metadata')[0]
    assert event['kind'] == 'db2_settings'
    assert event['host'] == 'db2.example.com'
    assert event['database_instance'] == 'db2.example.com:datadog'
    assert event['dbms'] == 'db2'
    assert event['dbms_version'] == '12.01.0400'
    assert event['collection_interval'] == 0.1
    assert 'foo:bar' in event['tags']
    assert all(not tag.startswith('db:') for tag in event['tags'])
    assert all(not tag.startswith('dd.internal') for tag in event['tags'])
    assert event['metadata'][0]['pending_change'] is False
    assert event['metadata'][1]['pending_change'] is True
    assert 'member' not in event['metadata'][1]


def test_db2_schema_payload(instance: dict[str, Any], aggregator: Any) -> None:
    instance.update(
        {
            'dbm': True,
            'collect_settings': {'enabled': False},
            'collect_schemas': {
                'enabled': True,
                'run_sync': True,
                'collection_interval': 0.1,
                'max_tables': 2,
                'max_columns': 2,
                'include_schemas': ['APP'],
            },
            'reported_hostname': 'db2.example.com',
            'database_identifier': {'template': '$resolved_hostname:$db'},
        }
    )
    check = IbmDb2Check('ibm_db2', {}, [instance])
    check._dbms_version = '12.01.0400'
    check.connection.query = mock.Mock(
        side_effect=[
            ([{'schema_name': 'APP', 'schema_owner': 'DB2INST1'}], []),
            (
                [
                    {
                        'schema_name': 'APP',
                        'table_name': 'PARENT',
                        'table_owner': 'DB2INST1',
                        'table_type': 'T',
                        'estimated_rows': 1,
                    },
                    {
                        'schema_name': 'APP',
                        'table_name': 'CHILD',
                        'table_owner': 'DB2INST1',
                        'table_type': 'T',
                        'estimated_rows': 1,
                    },
                ],
                [],
            ),
            (
                [
                    {
                        'schema_name': 'APP',
                        'table_name': 'PARENT',
                        'name': 'ID',
                        'ordinal': 0,
                        'typename': 'INTEGER',
                        'length': 4,
                        'scale': 0,
                        'nulls': 'N',
                        'default_value': None,
                    },
                    {
                        'schema_name': 'APP',
                        'table_name': 'CHILD',
                        'name': 'ID',
                        'ordinal': 0,
                        'typename': 'INTEGER',
                        'length': 4,
                        'scale': 0,
                        'nulls': 'N',
                        'default_value': None,
                    },
                    {
                        'schema_name': 'APP',
                        'table_name': 'CHILD',
                        'name': 'PARENT_ID',
                        'ordinal': 1,
                        'typename': 'INTEGER',
                        'length': 4,
                        'scale': 0,
                        'nulls': 'N',
                        'default_value': None,
                    },
                    {
                        'schema_name': 'APP',
                        'table_name': 'CHILD',
                        'name': 'EXTRA',
                        'ordinal': 2,
                        'typename': 'VARCHAR',
                        'length': 32,
                        'scale': 0,
                        'nulls': 'Y',
                        'default_value': None,
                    },
                ],
                [],
            ),
            (
                [
                    {
                        'index_schema': 'APP',
                        'name': 'PARENT_PK',
                        'schema_name': 'APP',
                        'table_name': 'PARENT',
                        'uniquerule': 'P',
                        'index_type': 'REG',
                        'column_count': 1,
                    },
                    {
                        'index_schema': 'APP',
                        'name': 'CHILD_PARENT_IDX',
                        'schema_name': 'APP',
                        'table_name': 'CHILD',
                        'uniquerule': 'D',
                        'index_type': 'REG',
                        'column_count': 1,
                    },
                ],
                [],
            ),
            (
                [
                    {
                        'index_schema': 'APP',
                        'index_name': 'PARENT_PK',
                        'name': 'ID',
                        'ordinal': 1,
                        'column_order': 'A',
                    },
                    {
                        'index_schema': 'APP',
                        'index_name': 'CHILD_PARENT_IDX',
                        'name': 'PARENT_ID',
                        'ordinal': 1,
                        'column_order': 'A',
                    },
                ],
                [],
            ),
            (
                [
                    {
                        'name': 'CHILD_PARENT_FK',
                        'schema_name': 'APP',
                        'table_name': 'CHILD',
                        'referenced_schema_name': 'APP',
                        'referenced_table_name': 'PARENT',
                        'referenced_key_name': 'PARENT_PK',
                        'delete_rule': 'A',
                        'update_rule': 'A',
                    }
                ],
                [],
            ),
            (
                [
                    {
                        'constraint_name': 'PARENT_PK',
                        'schema_name': 'APP',
                        'table_name': 'PARENT',
                        'name': 'ID',
                        'ordinal': 1,
                    },
                    {
                        'constraint_name': 'CHILD_PARENT_FK',
                        'schema_name': 'APP',
                        'table_name': 'CHILD',
                        'name': 'PARENT_ID',
                        'ordinal': 1,
                    },
                ],
                [],
            ),
        ]
    )

    check.dbm_metadata.run_job()

    event = aggregator.get_event_platform_events('dbm-metadata')[0]
    assert event['kind'] == 'db2_databases'
    assert event['host'] == 'db2.example.com'
    assert event['database_instance'] == 'db2.example.com:datadog'
    assert event['dbms'] == 'db2'
    assert event['dbms_version'] == '12.01.0400'
    assert event['collection_interval'] == 0.1
    assert event['collection_payloads_count'] == 1
    assert event['collection_started_at']

    tables = {
        database['schemas'][0]['tables'][0]['name']: database['schemas'][0]['tables'][0]
        for database in event['metadata']
    }
    assert tables['PARENT']['columns'][0]['data_type'] == 'INTEGER'
    assert tables['PARENT']['indexes'][0]['is_primary'] is True
    assert tables['PARENT']['indexes'][0]['columns'] == ['ID']
    assert len(tables['CHILD']['columns']) == 2
    assert tables['CHILD']['foreign_keys'][0]['referenced_table'] == 'APP.PARENT'
    assert tables['CHILD']['foreign_keys'][0]['column_names'] == ['PARENT_ID']
    assert 'FOREIGN KEY ("PARENT_ID")' in tables['CHILD']['foreign_keys'][0]['definition']


@pytest.mark.parametrize(
    'typename,length,scale,expected',
    [
        ('INTEGER', 4, 0, 'INTEGER'),
        ('VARCHAR', 32, 0, 'VARCHAR(32)'),
        ('DECIMAL', 10, 2, 'DECIMAL(10,2)'),
        (None, 10, 2, None),
    ],
)
def test_render_data_type(typename: str | None, length: int, scale: int, expected: str | None) -> None:
    assert _render_data_type(typename, length, scale) == expected


def test_db2_settings_ignored_patterns_use_bound_parameters(instance: dict[str, Any]) -> None:
    check = _dbm_check(instance)
    check.dbm_metadata._ignored_settings_patterns = ['diag%', 'mon_req%']
    check.connection.query = mock.Mock(return_value=([], []))

    check.dbm_metadata.run_job()

    query = check.connection.query.call_args.args[1]
    assert 'WHERE name NOT LIKE ? AND name NOT LIKE ?' in query
    assert check.connection.query.call_args.kwargs['params'] == ['diag%', 'mon_req%']


def test_db2_settings_disabled(instance: dict[str, Any], aggregator: Any) -> None:
    check = _dbm_check(instance)
    check.dbm_metadata._settings_enabled = False
    check.connection.query = mock.Mock(return_value=([], []))

    check.dbm_metadata.run_job()

    check.connection.query.assert_not_called()
    assert not aggregator.get_event_platform_events('dbm-metadata')
