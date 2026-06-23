# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json

import mock
import pytest

from datadog_checks.sap_hana import SapHanaCheck
from datadog_checks.sap_hana.diagnose import HanaConfigurationError

pytestmark = pytest.mark.unit

_BASE_INSTANCE = {
    'server': 'hana-host',
    'port': 39015,
    'username': 'dd',
    'password': 'pass',
}


def _make_check(extra=None):
    instance = dict(_BASE_INSTANCE)
    if extra:
        instance.update(extra)
    return SapHanaCheck('sap_hana', {}, [instance])


def _joined_row(
    schema,
    table,
    table_type='TABLE',
    is_column_table='TRUE',
    owner='OWNER',
    row_count=None,
    last_updated_on=None,
    column_name=None,
    data_type='INTEGER',
    nullable='TRUE',
    default=None,
    position=1,
):
    """Build one row of the streamed schema/tables/columns/stats join, in SELECT column order."""
    return (
        schema,
        table,
        table_type,
        is_column_table,
        owner,
        row_count,
        last_updated_on,
        column_name,
        data_type,
        nullable,
        default,
        position,
    )


def _make_cursor_mock(joined_rows, db_name='TEST_DB', description='Test database'):
    """Return a (conn, cursor) pair that streams the joined result set one row at a time via fetchone.

    The first fetchone call is consumed by the stats permission probe (returns a count row),
    followed by the database name, database description, joined rows, and end-of-cursor sentinel.
    """
    conn = mock.MagicMock()
    cursor = mock.MagicMock()
    conn.cursor.return_value = cursor
    # fetchone call order (all cursors share this queue since conn.cursor always returns the same mock):
    #   1. db_name       — _get_databases() CURRENT_DATABASE_QUERY
    #   2. description   — _get_databases() CURRENT_DATABASE_DESCRIPTION_QUERY
    #   3. (1,)          — _probe_stats_permission() COUNT probe
    #   4+. joined rows  — _get_cursor() pending_row + _get_next() iterations
    #   last. None       — end-of-cursor sentinel
    cursor.fetchone.side_effect = [(db_name,), (description,), (1,)] + list(joined_rows) + [None]
    return conn, cursor


def _collect_payloads(check):
    """Run collect_schemas() and return list of decoded payloads."""
    payloads = []
    check.database_monitoring_metadata = lambda raw: payloads.append(json.loads(raw))
    # suppress internal metrics so tests don't need a live aggregator
    check.histogram = mock.MagicMock()
    check.gauge = mock.MagicMock()
    check._schema_collection_job._schema_collector.collect_schemas()
    return payloads


# ─── Schema Collection ────────────────────────────────────────────────────────


class TestHanaSchemaCollector:
    def test_disabled_by_default(self):
        check = _make_check()
        assert not check._schema_collection_job._enabled

    def test_enabled_creates_collector(self):
        check = _make_check({'collect_schemas': {'enabled': True}})
        assert check._schema_collection_job._schema_collector is not None

    def test_payload_structure(self):
        check = _make_check({'collect_schemas': {'enabled': True}})
        check._conn, _ = _make_cursor_mock(
            [_joined_row('MY_SCHEMA', 'MY_TABLE', owner='MY_OWNER', column_name='COL1')],
        )

        payloads = _collect_payloads(check)

        assert len(payloads) == 1
        payload = payloads[0]
        assert payload['kind'] == 'saphana_databases'
        assert payload['dbms'] == 'saphana'
        assert payload['host'] == 'hana-host'
        assert payload['database_instance'] == 'hana-host:39015'

        row = payload['metadata'][0]
        assert row['name'] == 'TEST_DB'
        schema = row['schemas'][0]
        assert schema['name'] == 'MY_SCHEMA'
        assert schema['owner'] == 'MY_OWNER'
        table = schema['tables'][0]
        assert table['name'] == 'MY_TABLE'
        assert table['row_count'] is None
        assert table['last_updated_on'] is None
        assert table['columns'][0]['name'] == 'COL1'
        assert table['columns'][0]['data_type'] == 'INTEGER'
        assert table['columns'][0]['nullable'] is True

    def test_zero_column_table(self):
        # A table with no visible columns comes back as a single row with NULL column fields.
        check = _make_check({'collect_schemas': {'enabled': True}})
        check._conn, _ = _make_cursor_mock([_joined_row('S', 'EMPTY', column_name=None)])

        payloads = _collect_payloads(check)
        table = payloads[0]['metadata'][0]['schemas'][0]['tables'][0]
        assert table['name'] == 'EMPTY'
        assert table['columns'] == []

    def test_multiple_tables_streamed(self):
        check = _make_check({'collect_schemas': {'enabled': True}})
        check._conn, _ = _make_cursor_mock(
            [
                _joined_row('S', 'T1', column_name='C1', position=1),
                _joined_row('S', 'T1', column_name='C2', position=2),
                _joined_row('S', 'T2', column_name='C1', position=1),
            ],
        )

        payloads = _collect_payloads(check)
        tables = [t['name'] for row in payloads[0]['metadata'] for s in row['schemas'] for t in s['tables']]
        assert tables == ['T1', 'T2']

    def test_system_schemas_excluded_in_sql(self):
        check = _make_check({'collect_schemas': {'enabled': True}})
        query, params = check._schema_collection_job._schema_collector._query_builder.build()
        assert "NOT IN ('SYS', 'SYSTEM', 'PUBLIC')" in query
        assert r"NOT LIKE '\_SYS\_%' ESCAPE '\'" in query
        assert 'SYS.M_TABLES' in query
        assert 'SYS.VIEWS' in query
        assert 'SYS.VIEW_COLUMNS' in query
        # SYS.TABLES (without the M_) must not appear
        assert 'SYS.TABLES' not in query.replace('SYS.M_TABLES', '').replace('SYS.M_TABLE_STATISTICS', '')
        assert params == ()

    def test_exclude_schemas_filter_in_sql(self):
        check = _make_check({'collect_schemas': {'enabled': True, 'exclude_schemas': ['EXCL']}})
        query, params = check._schema_collection_job._schema_collector._query_builder.build()
        assert 'AND t.SCHEMA_NAME NOT IN (?)' in query
        assert 'AND v.SCHEMA_NAME NOT IN (?)' in query
        assert params == ('EXCL', 'EXCL')

    def test_include_schemas_filter_in_sql(self):
        check = _make_check({'collect_schemas': {'enabled': True, 'include_schemas': ['ONLY']}})
        query, params = check._schema_collection_job._schema_collector._query_builder.build()
        assert 'AND t.SCHEMA_NAME IN (?)' in query
        assert 'AND v.SCHEMA_NAME IN (?)' in query
        assert params == ('ONLY', 'ONLY')

    def test_max_columns_respected(self):
        check = _make_check({'collect_schemas': {'enabled': True, 'max_columns': 2}})
        check._conn, _ = _make_cursor_mock(
            [
                _joined_row('S', 'T', column_name='C1', position=1),
                _joined_row('S', 'T', column_name='C2', position=2),
                _joined_row('S', 'T', column_name='C3', position=3),
            ],
        )

        payloads = _collect_payloads(check)
        cols = payloads[0]['metadata'][0]['schemas'][0]['tables'][0]['columns']
        assert len(cols) == 2

    def test_max_tables_limit_in_sql(self):
        check = _make_check({'collect_schemas': {'enabled': True, 'max_tables': 3}})
        query, _ = check._schema_collection_job._schema_collector._query_builder.build()
        assert 'LIMIT 3' in query

    def test_max_views_limit_in_sql(self):
        check = _make_check({'collect_schemas': {'enabled': True, 'max_views': 7}})
        query, _ = check._schema_collection_job._schema_collector._query_builder.build()
        assert 'LIMIT 7' in query

    def test_schema_job_run_job_calls_collect_schemas(self):
        check = _make_check({'collect_schemas': {'enabled': True, 'run_sync': True}})
        job = check._schema_collection_job
        job._schema_collector.collect_schemas = mock.MagicMock()
        job._job_conn = mock.MagicMock()

        job.run_job()

        job._schema_collector.collect_schemas.assert_called_once()
        assert job._schema_collector._conn is job._job_conn

    def test_schema_job_resets_conn_on_hana_error(self):
        try:
            from hdbcli.dbapi import Error as HanaError
        except ImportError:
            HanaError = Exception

        check = _make_check({'collect_schemas': {'enabled': True, 'run_sync': True}})
        job = check._schema_collection_job
        job._job_conn = mock.MagicMock()
        job._schema_collector.collect_schemas = mock.MagicMock(side_effect=HanaError('connection lost'))

        with pytest.raises(HanaError):
            job.run_job()

        assert job._job_conn is None
        assert job._schema_collector._conn is None

    def test_schema_job_disabled_does_not_run(self):
        check = _make_check()
        job = check._schema_collection_job
        assert not job._enabled

    def test_column_field_mapping(self):
        COLUMNS = [
            # (name ~20 chars,         data_type,    nullable,  default,                position)
            ('EMPLOYEE_IDENTIFIER', 'INTEGER', 'FALSE', None, 1),
            ('CUSTOMER_FIRST_NAME', 'NVARCHAR', 'TRUE', None, 2),
            ('RECORD_CREATED_TIME', 'TIMESTAMP', 'TRUE', 'CURRENT_TIMESTAMP', 3),
            ('ACCOUNT_BALANCE_AMT', 'DECIMAL', 'TRUE', '0', 4),
            ('CUSTOMER_STATUS_CODE', 'VARCHAR', 'FALSE', 'ACTIVE', 5),
            ('IS_ACTIVE_FLAG_VALUE', 'BOOLEAN', 'TRUE', 'FALSE', 6),
            ('TOTAL_AMOUNT_NUMERIC', 'BIGINT', 'FALSE', None, 7),
            ('PRODUCT_CODE_STRING', 'CHAR', 'TRUE', None, 8),
            ('CONVERSION_RATIO_VAL', 'DOUBLE', 'FALSE', '1.0', 9),
            ('LONG_TEXT_NOTES_CLOB', 'CLOB', 'TRUE', None, 10),
            ('LAST_MODIFIED_DTTM', 'TIMESTAMP', 'TRUE', None, 11),
            ('RECORD_TYPE_TINYINT', 'TINYINT', 'FALSE', '0', 12),
            ('BINARY_PAYLOAD_DATA', 'BLOB', 'TRUE', None, 13),
            ('NULL_TYPED_COLUMN_AA', None, 'TRUE', None, 14),  # None → ''
            ('LAST_SEQUENCE_NUMBER', 'SMALLINT', 'FALSE', None, 15),
        ]
        rows = [
            _joined_row('S', 'T', column_name=name, data_type=dt, nullable=nl, default=d, position=pos)
            for name, dt, nl, d, pos in COLUMNS
        ]
        check = _make_check({'collect_schemas': {'enabled': True, 'max_columns': 100}})
        check._conn, _ = _make_cursor_mock(rows)

        payloads = _collect_payloads(check)
        cols = payloads[0]['metadata'][0]['schemas'][0]['tables'][0]['columns']

        assert len(cols) == len(COLUMNS)
        for col, (name, data_type, nullable, default, position) in zip(cols, COLUMNS):
            assert col['name'] == name
            assert col['data_type'] == (data_type or '')
            assert col['nullable'] == (nullable == 'TRUE')
            assert col['default'] == default
            assert col['position'] == position

    def test_column_multi_table_mapping(self):
        rows = [
            _joined_row('S', 'T1', column_name='C1', data_type='INTEGER', nullable='TRUE', position=1),
            _joined_row('S', 'T1', column_name='C2', data_type='VARCHAR', nullable='TRUE', position=2),
            _joined_row('S', 'T1', column_name='C3', data_type='TIMESTAMP', nullable='FALSE', position=3),
            _joined_row('S', 'T2', column_name='X1', data_type='BIGINT', nullable='FALSE', position=1),
            _joined_row('S', 'T2', column_name='X2', data_type='DECIMAL', nullable='TRUE', default='0', position=2),
        ]
        check = _make_check({'collect_schemas': {'enabled': True}})
        check._conn, _ = _make_cursor_mock(rows)

        payloads = _collect_payloads(check)
        tables = {t['name']: t for row in payloads[0]['metadata'] for s in row['schemas'] for t in s['tables']}

        assert set(tables.keys()) == {'T1', 'T2'}
        assert [c['name'] for c in tables['T1']['columns']] == ['C1', 'C2', 'C3']
        assert tables['T1']['columns'][2]['nullable'] is False
        assert [c['name'] for c in tables['T2']['columns']] == ['X1', 'X2']
        assert tables['T2']['columns'][1]['default'] == '0'

    def test_get_databases_name_and_description(self):
        check = _make_check({'collect_schemas': {'enabled': True}})
        conn = mock.MagicMock()
        cursor = mock.MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchone.side_effect = [('PROD_DB',), ('Production instance',)]
        check._conn = conn

        result = check._schema_collection_job._schema_collector._get_databases()
        assert result == [{'name': 'PROD_DB', 'description': 'Production instance'}]

    def test_get_databases_description_query_fails(self):
        check = _make_check({'collect_schemas': {'enabled': True}})
        conn = mock.MagicMock()
        cursor = mock.MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = ('PROD_DB',)

        def raise_on_description(query, *args, **kwargs):
            if 'DESCRIPTION' in query:
                raise Exception('access denied')

        cursor.execute.side_effect = raise_on_description
        check._conn = conn

        result = check._schema_collection_job._schema_collector._get_databases()
        assert result == [{'name': 'PROD_DB', 'description': ''}]

    def test_get_databases_execute_exception_skips_collection(self):
        check = _make_check({'collect_schemas': {'enabled': True}})
        conn = mock.MagicMock()
        cursor = mock.MagicMock()
        conn.cursor.return_value = cursor
        cursor.execute.side_effect = Exception('connection error')
        check._conn = conn

        # No hostname fallback: an unreadable current database skips collection entirely.
        result = check._schema_collection_job._schema_collector._get_databases()
        assert result == []

    def test_get_databases_no_rows_skips_collection(self):
        check = _make_check({'collect_schemas': {'enabled': True}})
        conn = mock.MagicMock()
        cursor = mock.MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = None
        check._conn = conn

        result = check._schema_collection_job._schema_collector._get_databases()
        assert result == []

    def test_is_column_table_false(self):
        check = _make_check({'collect_schemas': {'enabled': True}})
        check._conn, _ = _make_cursor_mock([_joined_row('S', 'T', is_column_table='FALSE', column_name='C1')])

        payloads = _collect_payloads(check)
        table = payloads[0]['metadata'][0]['schemas'][0]['tables'][0]
        assert table['is_column_table'] is False

    def test_null_schema_owner(self):
        check = _make_check({'collect_schemas': {'enabled': True}})
        check._conn, _ = _make_cursor_mock([_joined_row('S', 'T', owner=None, column_name='C1')])

        payloads = _collect_payloads(check)
        schema = payloads[0]['metadata'][0]['schemas'][0]
        assert schema['owner'] == ''

    def test_include_and_exclude_combined(self):
        check = _make_check({'collect_schemas': {'enabled': True, 'include_schemas': ['A'], 'exclude_schemas': ['B']}})
        query, params = check._schema_collection_job._schema_collector._query_builder.build()
        assert 'AND t.SCHEMA_NAME IN (?)' in query
        assert 'AND t.SCHEMA_NAME NOT IN (?)' in query
        assert 'AND v.SCHEMA_NAME IN (?)' in query
        assert 'AND v.SCHEMA_NAME NOT IN (?)' in query
        assert params == ('A', 'B', 'A', 'B')

    def test_row_count_in_payload(self):
        check = _make_check({'collect_schemas': {'enabled': True}})
        check._conn, _ = _make_cursor_mock([_joined_row('S', 'T', row_count=42, column_name='C1')])

        payloads = _collect_payloads(check)
        table = payloads[0]['metadata'][0]['schemas'][0]['tables'][0]
        assert table['row_count'] == 42

    def test_last_updated_on_in_payload(self):
        check = _make_check({'collect_schemas': {'enabled': True}})
        check._conn, _ = _make_cursor_mock(
            [_joined_row('S', 'T', last_updated_on='2024-01-15 12:00:00', column_name='C1')]
        )

        payloads = _collect_payloads(check)
        table = payloads[0]['metadata'][0]['schemas'][0]['tables'][0]
        assert table['last_updated_on'] == '2024-01-15 12:00:00'

    def test_view_in_payload(self):
        check = _make_check({'collect_schemas': {'enabled': True}})
        check._conn, _ = _make_cursor_mock(
            [
                _joined_row(
                    'S', 'MY_VIEW', table_type='VIEW', is_column_table=None, column_name='V_COL', data_type='NVARCHAR'
                ),
            ]
        )

        payloads = _collect_payloads(check)
        table = payloads[0]['metadata'][0]['schemas'][0]['tables'][0]
        assert table['name'] == 'MY_VIEW'
        assert table['type'] == 'VIEW'
        assert table['is_column_table'] is False
        assert table['row_count'] is None
        assert table['last_updated_on'] is None
        assert table['columns'][0]['name'] == 'V_COL'
        assert table['columns'][0]['data_type'] == 'NVARCHAR'

    def test_view_no_columns(self):
        check = _make_check({'collect_schemas': {'enabled': True}})
        check._conn, _ = _make_cursor_mock([_joined_row('S', 'MY_VIEW', table_type='VIEW', is_column_table=None)])

        payloads = _collect_payloads(check)
        table = payloads[0]['metadata'][0]['schemas'][0]['tables'][0]
        assert table['name'] == 'MY_VIEW'
        assert table['columns'] == []

    def test_stats_join_when_available(self):
        check = _make_check({'collect_schemas': {'enabled': True}})
        check._schema_collection_job._schema_collector._query_builder._has_table_statistics = True
        query, _ = check._schema_collection_job._schema_collector._query_builder.build()
        assert 'SYS.M_TABLE_STATISTICS' in query
        assert 'ts.LAST_MODIFY_TIME' in query

    def test_stats_join_omitted_when_unavailable(self):
        check = _make_check({'collect_schemas': {'enabled': True}})
        check._schema_collection_job._schema_collector._query_builder._has_table_statistics = False
        query, _ = check._schema_collection_job._schema_collector._query_builder.build()
        assert 'SYS.M_TABLE_STATISTICS' not in query
        assert 'NULL AS LAST_UPDATED_ON' in query

    def test_column_chunk_flush(self):
        # 3 tables × 3 columns each; threshold set to 5 so flush fires after T1+T2 (6 cols),
        # then T3 lands in the final payload. Verifies intermediate flush, correct table
        # distribution, and that collection_payloads_count only appears on the last payload.
        rows = [
            _joined_row('S', 'T1', column_name='C1', position=1),
            _joined_row('S', 'T1', column_name='C2', position=2),
            _joined_row('S', 'T1', column_name='C3', position=3),
            _joined_row('S', 'T2', column_name='C1', position=1),
            _joined_row('S', 'T2', column_name='C2', position=2),
            _joined_row('S', 'T2', column_name='C3', position=3),
            _joined_row('S', 'T3', column_name='C1', position=1),
            _joined_row('S', 'T3', column_name='C2', position=2),
            _joined_row('S', 'T3', column_name='C3', position=3),
        ]
        check = _make_check({'collect_schemas': {'enabled': True}})
        check._schema_collection_job._schema_collector._config.payload_column_chunk_size = 5
        check._conn, _ = _make_cursor_mock(rows)

        payloads = _collect_payloads(check)

        assert len(payloads) == 2
        tables_p1 = [t['name'] for row in payloads[0]['metadata'] for s in row['schemas'] for t in s['tables']]
        tables_p2 = [t['name'] for row in payloads[1]['metadata'] for s in row['schemas'] for t in s['tables']]
        assert tables_p1 == ['T1', 'T2']
        assert tables_p2 == ['T3']
        assert 'collection_payloads_count' not in payloads[0]
        assert payloads[1]['collection_payloads_count'] == 2


# ─── Diagnostics ─────────────────────────────────────────────────────────────


class TestHanaDiagnose:
    def _run(self, check):
        check.diagnosis.clear()
        results = check.diagnosis.run_explicit()
        return {r.name: r for r in results}

    def _healthy_conn(self):
        conn = mock.MagicMock()
        cursor = mock.MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = ('2.00.076.00 (fa/CE2024)',)
        return conn

    def test_connection_failure(self):
        check = _make_check()
        check.get_connection = mock.MagicMock(return_value=None)

        results = self._run(check)
        r = results[HanaConfigurationError.connection_failure.value]
        assert r.result == 1  # DIAGNOSIS_FAIL

    def test_healthy_instance_all_pass(self):
        check = _make_check()
        check.get_connection = mock.MagicMock(return_value=self._healthy_conn())

        results = self._run(check)
        assert results[HanaConfigurationError.connection_failure.value].result == 0
        assert results[HanaConfigurationError.version_unsupported.value].result == 0
        for view in (
            'sys_schemas_accessible',
            'sys_m_tables_accessible',
            'sys_views_accessible',
            'sys_table_columns_accessible',
            'sys_view_columns_accessible',
        ):
            assert results[view].result == 0

    def test_unsupported_hana_version(self):
        check = _make_check()
        conn = mock.MagicMock()
        cursor = mock.MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = ('1.00.122.00',)  # HANA 1.x
        check.get_connection = mock.MagicMock(return_value=conn)

        results = self._run(check)
        assert results[HanaConfigurationError.version_unsupported.value].result == 1

    def test_version_query_privilege_error_not_version_unsupported(self):
        check = _make_check()
        conn = mock.MagicMock()
        cursor = mock.MagicMock()
        conn.cursor.return_value = cursor

        def execute_side_effect(query, *args, **kwargs):
            if 'VERSION' in query and 'M_DATABASE' in query:
                raise Exception('insufficient privilege: Not authorized')

        cursor.execute.side_effect = execute_side_effect
        check.get_connection = mock.MagicMock(return_value=conn)

        results = self._run(check)
        # A privilege error reading the version must map to the privilege diagnostic,
        # not a misleading "version unsupported" result.
        assert HanaConfigurationError.version_unsupported.value not in results
        assert results[HanaConfigurationError.missing_catalog_privilege.value].result == 1

    def test_privilege_error_on_catalog_view(self):
        check = _make_check()
        conn = mock.MagicMock()
        cursor = mock.MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = ('2.00.076.00',)

        def execute_side_effect(query, *args, **kwargs):
            if 'COUNT' in query and 'M_TABLES' in query:
                raise Exception('insufficient privilege: Not authorized')

        cursor.execute.side_effect = execute_side_effect
        check.get_connection = mock.MagicMock(return_value=conn)

        results = self._run(check)
        assert results['sys_m_tables_accessible'].result == 1
        # remediation should mention privilege
        assert results['sys_m_tables_accessible'].remediation

    def test_catalog_inaccessible_generic_error(self):
        check = _make_check()
        conn = mock.MagicMock()
        cursor = mock.MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = ('2.00.076.00',)

        def execute_side_effect(query, *args, **kwargs):
            if 'COUNT' in query and 'M_TABLES' in query:
                raise Exception('connection timeout')

        cursor.execute.side_effect = execute_side_effect
        check.get_connection = mock.MagicMock(return_value=conn)

        results = self._run(check)
        assert results['sys_m_tables_accessible'].result == 1

    def test_properties(self):
        check = _make_check()
        assert check.reported_hostname == 'hana-host'
        assert check.database_identifier == 'hana-host:39015'
        assert check.dbms == 'saphana'
        assert check.cloud_metadata == {}
        assert 'server:hana-host' in check.tags
