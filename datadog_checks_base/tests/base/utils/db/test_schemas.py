# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import contextmanager

import pytest

from datadog_checks.base.checks.db import DatabaseCheck
from datadog_checks.base.utils.db.schemas import SchemaCollector, SchemaCollectorConfig

try:
    import datadog_agent  # type: ignore
except ImportError:
    from datadog_checks.base.stubs import datadog_agent


class TestDatabaseCheck(DatabaseCheck):
    __test__ = False

    def __init__(self):
        super().__init__()
        self._reported_hostname = "test_hostname"
        self._database_identifier = "test_database_identifier"
        self._dbms_version = "test_dbms_version"
        self._agent_version = "test_agent_version"
        self._tags = ["test_tag"]
        self._cloud_metadata = {"test_cloud_metadata": "test_cloud_metadata"}

    @property
    def reported_hostname(self):
        return self._reported_hostname

    @property
    def database_identifier(self):
        return self._database_identifier

    @property
    def dbms_version(self):
        return self._dbms_version

    @property
    def agent_version(self):
        return self._agent_version

    @property
    def tags(self):
        return self._tags

    @property
    def cloud_metadata(self):
        return self._cloud_metadata


class TestSchemaCollector(SchemaCollector):
    __test__ = False

    def __init__(self, check: DatabaseCheck, config: SchemaCollectorConfig):
        super().__init__(check, config)
        self._row_index = 0
        self._rows = [{'table_name': 'test_table'}]

    def _get_databases(self):
        return [{'name': 'test_database'}]

    @contextmanager
    def _get_cursor(self, database: str):
        yield {}

    def _get_next(self, _cursor):
        if self._row_index < len(self._rows):
            row = self._rows[self._row_index]
            self._row_index += 1
            return row
        return None

    def _map_row(self, database: str, cursor_row: dict):
        return {**database, "tables": [cursor_row]}

    @property
    def kind(self):
        return "test_databases"


class TestSchemaCollectorEmptyLastDb(TestSchemaCollector):
    """Simulates multiple databases where the last one has no tables."""

    __test__ = False

    def __init__(self, check, config):
        super().__init__(check, config)
        self._db_rows = {
            'db_with_tables': [{'table_name': 'users'}, {'table_name': 'orders'}],
            'db_empty_last': [],
        }
        self._current_rows = []

    def _get_databases(self):
        return [{'name': 'db_with_tables'}, {'name': 'db_empty_last'}]

    @contextmanager
    def _get_cursor(self, database: str):
        self._current_rows = list(self._db_rows.get(database, []))
        self._row_index = 0
        yield {}

    def _get_next(self, _cursor):
        if self._row_index < len(self._current_rows):
            row = self._current_rows[self._row_index]
            self._row_index += 1
            return row
        return None


class TestSchemaCollectorWithInaccessibleDb(TestSchemaCollector):
    """Simulates multiple databases where one raises an error on cursor open."""

    __test__ = False

    def __init__(self, check, config):
        super().__init__(check, config)
        self._current_rows = []

    def _get_databases(self):
        return [{'name': 'db_accessible'}, {'name': 'db_inaccessible'}, {'name': 'db_also_accessible'}]

    @contextmanager
    def _get_cursor(self, database: str):
        if database == 'db_inaccessible':
            raise RuntimeError("Cannot open database version 852")
        self._current_rows = [{'table_name': 'users'}]
        self._row_index = 0
        yield {}

    def _get_next(self, _cursor):
        if self._row_index < len(self._current_rows):
            row = self._current_rows[self._row_index]
            self._row_index += 1
            return row
        return None


class TestSchemaCollectorMidIterationFailure(TestSchemaCollector):
    """Simulates a database that fails mid-iteration after at least one chunk has been flushed."""

    __test__ = False

    def _get_databases(self):
        return [{'name': 'db_partial_fail'}, {'name': 'db_ok'}]

    @contextmanager
    def _get_cursor(self, database: str):
        self._rows = [{'table_name': 'first'}, {'table_name': 'second'}]
        self._row_index = 0
        yield {}

    def _map_row(self, database, cursor_row):
        if database['name'] == 'db_partial_fail' and cursor_row.get('table_name') == 'second':
            raise RuntimeError("mid-iteration error after first chunk flushed")
        return super()._map_row(database, cursor_row)


@pytest.mark.unit
def test_schema_collector(aggregator):
    check = TestDatabaseCheck()
    collector = TestSchemaCollector(check, SchemaCollectorConfig())
    collector.collect_schemas()

    events = aggregator.get_event_platform_events("dbm-metadata")
    assert len(events) == 1
    event = events[0]
    assert event['kind'] == collector.kind
    assert event['host'] == check.reported_hostname
    assert event['database_instance'] == check.database_identifier
    assert event['agent_version'] == datadog_agent.get_version()
    assert event['collection_interval'] == collector._config.collection_interval
    assert event['dbms_version'] == check.dbms_version
    assert event['tags'] == check.tags
    assert event['cloud_metadata'] == check.cloud_metadata
    assert event['metadata'][0]['name'] == 'test_database'
    assert event['metadata'][0]['tables'][0]['table_name'] == 'test_table'


@pytest.mark.unit
def test_schema_collector_empty_last_database(aggregator):
    """Verify that each database sends its own terminal payload, even when it returns 0 rows."""
    check = TestDatabaseCheck()
    collector = TestSchemaCollectorEmptyLastDb(check, SchemaCollectorConfig())
    collector.collect_schemas()

    events = aggregator.get_event_platform_events("dbm-metadata")
    assert len(events) == 2, "Expected 2 payloads (one per database) but got {}".format(len(events))
    assert len(events[0]['metadata']) == 2
    assert events[0]['metadata'][0]['name'] == 'db_with_tables'
    assert events[0]['metadata'][0]['tables'][0]['table_name'] == 'users'
    assert events[0]['metadata'][1]['name'] == 'db_with_tables'
    assert events[0]['metadata'][1]['tables'][0]['table_name'] == 'orders'
    assert events[0]['collection_payloads_count'] == 1
    assert len(events[1]['metadata']) == 0
    assert events[1]['collection_payloads_count'] == 1


@pytest.mark.unit
def test_schema_collector_chunk_size_flush(aggregator):
    """Verify that collection_payloads_count is set even when all rows are flushed by chunk size."""
    check = TestDatabaseCheck()
    config = SchemaCollectorConfig()
    config.payload_chunk_size = 1
    collector = TestSchemaCollector(check, config)
    collector.collect_schemas()

    events = aggregator.get_event_platform_events("dbm-metadata")
    # chunk_size=1 flushes the single row mid-loop, then a final payload marks the snapshot
    assert len(events) == 2
    assert 'collection_payloads_count' not in events[0]
    assert events[-1]['collection_payloads_count'] == len(events)


@pytest.mark.unit
def test_schema_collector_mid_iteration_failure(aggregator):
    """Verify chunk payloads sent before a mid-iteration failure are counted correctly."""
    check = TestDatabaseCheck()
    config = SchemaCollectorConfig()
    config.payload_chunk_size = 1
    collector = TestSchemaCollectorMidIterationFailure(check, config)
    result = collector.collect_schemas()

    assert result is True
    events = aggregator.get_event_platform_events("dbm-metadata")
    # db_partial_fail: 1 orphaned chunk (no terminal), db_ok: 2 chunks + 1 terminal
    assert len(events) == 4

    partial_fail_events = [e for e in events if any(r.get('name') == 'db_partial_fail' for r in e['metadata'])]
    ok_events = [e for e in events if any(r.get('name') == 'db_ok' for r in e['metadata'])]
    terminal_events = [e for e in events if 'collection_payloads_count' in e]

    assert len(partial_fail_events) == 1
    assert 'collection_payloads_count' not in partial_fail_events[0]
    assert len(ok_events) == 2
    assert len(terminal_events) == 1
    assert terminal_events[0]['collection_payloads_count'] == 3


@pytest.mark.unit
def test_schema_collector_skips_inaccessible_database(aggregator):
    """An inaccessible database is skipped and collection continues for the remaining databases."""
    check = TestDatabaseCheck()
    collector = TestSchemaCollectorWithInaccessibleDb(check, SchemaCollectorConfig())
    result = collector.collect_schemas()

    assert result is True
    events = aggregator.get_event_platform_events("dbm-metadata")
    assert len(events) == 2
    collected_names = [row['name'] for event in events for row in event['metadata']]
    assert 'db_accessible' in collected_names
    assert 'db_also_accessible' in collected_names
    assert 'db_inaccessible' not in collected_names


@pytest.mark.unit
def test_schema_collector_skips_malformed_database_entry(aggregator):
    """A database entry missing the 'name' key is skipped without aborting the run."""

    class MalformedDbCollector(TestSchemaCollector):
        __test__ = False

        def _get_databases(self):
            return [{'name': 'db_good'}, {'no_name_key': 'bad'}, {'name': 'db_also_good'}]

        @contextmanager
        def _get_cursor(self, database: str):
            self._row_index = 0
            yield {}

    check = TestDatabaseCheck()
    collector = MalformedDbCollector(check, SchemaCollectorConfig())
    result = collector.collect_schemas()

    assert result is True
    events = aggregator.get_event_platform_events("dbm-metadata")
    collected_names = [row['name'] for event in events for row in event['metadata']]
    assert 'db_good' in collected_names
    assert 'db_also_good' in collected_names
