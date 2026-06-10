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
    column_name=None,
    data_type='INTEGER',
    nullable='TRUE',
    default=None,
    position=1,
):
    """Build one row of the streamed schema/tables/columns join, in SELECT column order."""
    return (schema, table, table_type, is_column_table, owner, column_name, data_type, nullable, default, position)


def _make_cursor_mock(joined_rows, db_name='TEST_DB', description='Test database'):
    """Return a (conn, cursor) pair that streams the joined result set one row at a time via fetchone."""
    conn = mock.MagicMock()
    cursor = mock.MagicMock()
    conn.cursor.return_value = cursor
    # fetchone order: database name, database description, then the joined rows, then end-of-cursor.
    cursor.fetchone.side_effect = [(db_name,), (description,)] + list(joined_rows) + [None]
    return conn, cursor


def _collect_payloads(check):
    """Run collect_schemas() and return list of decoded payloads."""
    payloads = []
    check.database_monitoring_metadata = lambda raw: payloads.append(json.loads(raw))
    # suppress internal metrics so tests don't need a live aggregator
    check.histogram = mock.MagicMock()
    check.gauge = mock.MagicMock()
    check._schema_collector.collect_schemas()
    return payloads


# ─── Schema Collection ────────────────────────────────────────────────────────


class TestHanaSchemaCollector:
    def test_disabled_by_default(self):
        check = _make_check()
        assert check._schema_collector is None

    def test_enabled_creates_collector(self):
        check = _make_check({'collect_schemas': {'enabled': True}})
        assert check._schema_collector is not None

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
        query, params = check._schema_collector._build_query()
        assert "NOT IN ('SYS', 'SYSTEM', 'PUBLIC')" in query
        assert r"NOT LIKE '\_SYS\_%' ESCAPE '\'" in query
        assert params == ()

    def test_exclude_schemas_filter_in_sql(self):
        check = _make_check({'collect_schemas': {'enabled': True, 'exclude_schemas': ['EXCL']}})
        query, params = check._schema_collector._build_query()
        assert 'AND t.SCHEMA_NAME NOT IN (?)' in query
        assert params == ('EXCL',)

    def test_include_schemas_filter_in_sql(self):
        check = _make_check({'collect_schemas': {'enabled': True, 'include_schemas': ['ONLY']}})
        query, params = check._schema_collector._build_query()
        assert 'AND t.SCHEMA_NAME IN (?)' in query
        assert params == ('ONLY',)

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
        query, _ = check._schema_collector._build_query()
        assert 'LIMIT 3' in query

    def test_maybe_collect_schemas_time_gated(self):
        check = _make_check({'collect_schemas': {'enabled': True, 'collection_interval': 600}})
        check._conn, _ = _make_cursor_mock([_joined_row('S', 'T', column_name='C1')])
        check.database_monitoring_metadata = mock.MagicMock()
        check.histogram = mock.MagicMock()
        check.gauge = mock.MagicMock()

        # First call triggers collection (last time = 0)
        check._maybe_collect_schemas()
        assert check.database_monitoring_metadata.call_count == 1

        # Immediate second call is gated
        check._maybe_collect_schemas()
        assert check.database_monitoring_metadata.call_count == 1

    def test_maybe_collect_schemas_skips_without_connection(self):
        check = _make_check({'collect_schemas': {'enabled': True}})
        check._conn = None
        check.database_monitoring_metadata = mock.MagicMock()
        check._maybe_collect_schemas()
        check.database_monitoring_metadata.assert_not_called()


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
        for view in ('sys_schemas_accessible', 'sys_tables_accessible', 'sys_table_columns_accessible'):
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

    def test_privilege_error_on_catalog_view(self):
        check = _make_check()
        conn = mock.MagicMock()
        cursor = mock.MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = ('2.00.076.00',)

        def execute_side_effect(query, *args, **kwargs):
            if 'COUNT' in query and 'SCHEMAS' in query:
                raise Exception('insufficient privilege: Not authorized')

        cursor.execute.side_effect = execute_side_effect
        check.get_connection = mock.MagicMock(return_value=conn)

        results = self._run(check)
        assert results['sys_schemas_accessible'].result == 1
        # remediation should mention privilege
        assert results['sys_schemas_accessible'].remediation

    def test_catalog_inaccessible_generic_error(self):
        check = _make_check()
        conn = mock.MagicMock()
        cursor = mock.MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = ('2.00.076.00',)

        def execute_side_effect(query, *args, **kwargs):
            if 'COUNT' in query and 'TABLES' in query:
                raise Exception('connection timeout')

        cursor.execute.side_effect = execute_side_effect
        check.get_connection = mock.MagicMock(return_value=conn)

        results = self._run(check)
        assert results['sys_tables_accessible'].result == 1

    def test_properties(self):
        check = _make_check()
        assert check.reported_hostname == 'hana-host'
        assert check.database_identifier == 'hana-host:39015'
        assert check.dbms == 'saphana'
        assert check.cloud_metadata == {}
        assert 'server:hana-host' in check.tags
