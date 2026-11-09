# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Collection, Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import Any

import pytest

from datadog_checks.base.checks.db import DatabaseCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.utils.db.schemas import (
    DatabaseSchemaCollector,
    SchemaCollector,
    SchemaCollectorConfig,
    SchemaObjectCollector,
    ViewObjectCollector,
)

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
        self.tag_manager.set_tags_from_list(
            ["test_tag", "db:test_db", "dd.internal.resource:database_instance:test_hostname"]
        )
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
    def cloud_metadata(self):
        return self._cloud_metadata


class TestCheckWithoutTagManager(TestDatabaseCheck):
    __test__ = False

    def __init__(self):
        super().__init__()
        self.tag_manager = None

    @property
    def tags(self):
        return ["test_tag", "db:test_db"]


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
    assert event['tags'] == ['test_tag']
    assert event['cloud_metadata'] == check.cloud_metadata
    assert event['metadata'][0]['name'] == 'test_database'
    assert event['metadata'][0]['tables'][0]['table_name'] == 'test_table'


@pytest.mark.unit
def test_schema_collector_uses_check_tags_without_tag_manager(aggregator):
    """Checks that keep their own tag list, rather than a `TagManager`, still send those tags."""
    check = TestCheckWithoutTagManager()
    TestSchemaCollector(check, SchemaCollectorConfig()).collect_schemas()

    events = aggregator.get_event_platform_events("dbm-metadata")
    assert events[0]['tags'] == check.tags


@pytest.mark.unit
def test_schema_collector_tags_telemetry_with_kind(aggregator):
    check = TestDatabaseCheck()
    collector = TestSchemaCollector(check, SchemaCollectorConfig())
    collector.collect_schemas()

    tags = check.tags + ["status:success", "kind:test_databases"]
    for metric in ("schema.time", "schema.tables_count", "schema.payloads_count"):
        aggregator.assert_metric(f"dd.{check.dbms}.{metric}", tags=tags, hostname=check.reported_hostname)


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


class FakeSession:
    """Stands in for a per-database connection and records the queries run on it."""

    def __init__(self, database_name: str):
        self.database_name = database_name
        self.queries: list[str] = []


class FakeTablesCollector(SchemaObjectCollector):
    def __init__(
        self,
        check: DatabaseCheck,
        config: SchemaCollectorConfig,
        rows_by_database: Mapping[str, Sequence[str]],
        fail_on: Collection[tuple[str, str]] = (),
    ):
        super().__init__(check, config)
        self._rows_by_database = rows_by_database
        self._fail_on = set(fail_on)

    @property
    def kind(self) -> str:
        return "test_databases"

    @contextmanager
    def _open_rows(self, session: FakeSession, database_name: str) -> Iterator[Iterator[str]]:
        session.queries.append(self.kind)
        yield self._iter_rows(database_name)

    def _iter_rows(self, database_name: str) -> Iterator[str]:
        for row in self._rows_by_database.get(database_name, []):
            if (database_name, row) in self._fail_on:
                raise RuntimeError(f"{self.kind} query failed")
            yield row

    def _map_row(self, database: dict[str, Any], cursor_row: str) -> dict[str, Any]:
        return {**database, "tables": [{"name": cursor_row}]}


class FakeViewsCollector(ViewObjectCollector, FakeTablesCollector):
    @property
    def kind(self) -> str:
        return "test_views"

    def _map_row(self, database: dict[str, Any], cursor_row: str) -> dict[str, Any]:
        view = {"name": cursor_row, "definition": "SELECT 1", "columns": []}
        return {**database, "schemas": [self._schema_with_view({"name": "public"}, view)]}


class FakeDatabaseCollector(DatabaseSchemaCollector):
    def __init__(
        self,
        check: DatabaseCheck,
        object_collectors: Sequence[SchemaObjectCollector],
        databases: Sequence[str],
        unopenable: Collection[str] = (),
    ):
        super().__init__(check, object_collectors)
        self._databases = databases
        self._unopenable = set(unopenable)
        self.get_databases_calls = 0
        self.sessions: list[FakeSession] = []

    def _get_databases(self) -> list[dict[str, Any]]:
        self.get_databases_calls += 1
        return [{"name": name} for name in self._databases]

    @contextmanager
    def _open_database(self, database_name: str) -> Iterator[FakeSession]:
        if database_name in self._unopenable:
            raise RuntimeError(f"cannot open {database_name}")
        session = FakeSession(database_name)
        self.sessions.append(session)
        yield session


def events_by_kind(aggregator: AggregatorStub) -> dict[str, list[dict[str, Any]]]:
    events: dict[str, list[dict[str, Any]]] = {}
    for event in aggregator.get_event_platform_events("dbm-metadata"):
        events.setdefault(event["kind"], []).append(event)
    return events


def snapshot_names(events: Sequence[dict[str, Any]]) -> list[str | None]:
    """
    Names of the databases whose snapshot was completed by a terminal payload, in collection order.

    A terminal payload is empty when the rows were already flushed in chunks, so the name comes from the latest
    payload that had rows.
    """
    completed: list[str | None] = []
    current: str | None = None
    for event in events:
        if event["metadata"]:
            current = event["metadata"][0]["name"]
        if "collection_payloads_count" in event:
            completed.append(current)
    return completed


@pytest.mark.unit
def test_database_collector_opens_each_database_once_for_all_kinds(aggregator: AggregatorStub):
    check = TestDatabaseCheck()
    rows = {"db1": ["a"], "db2": ["b"]}
    tables = FakeTablesCollector(check, SchemaCollectorConfig(), rows)
    views = FakeViewsCollector(check, SchemaCollectorConfig(), rows)
    collector = FakeDatabaseCollector(check, [tables, views], ["db1", "db2"])

    assert collector.collect_schemas() is True

    assert collector.get_databases_calls == 1
    assert [(s.database_name, s.queries) for s in collector.sessions] == [
        ("db1", ["test_databases", "test_views"]),
        ("db2", ["test_databases", "test_views"]),
    ]
    events = events_by_kind(aggregator)
    assert snapshot_names(events["test_databases"]) == ["db1", "db2"]
    assert snapshot_names(events["test_views"]) == ["db1", "db2"]
    view_schema = events["test_views"][0]["metadata"][0]["schemas"][0]
    assert view_schema["tables"] == []
    assert view_schema["views"][0]["name"] == "a"


@pytest.mark.unit
def test_database_collector_kind_failure_skips_only_that_kind(aggregator: AggregatorStub):
    """A kind failing partway through a database leaves its snapshot incomplete without affecting other kinds."""
    check = TestDatabaseCheck()
    config = SchemaCollectorConfig()
    config.payload_chunk_size = 1
    rows = {"db1": ["first", "second"], "db2": ["third"]}
    tables = FakeTablesCollector(check, config, rows, fail_on=[("db1", "second")])
    views = FakeViewsCollector(check, config, rows)
    collector = FakeDatabaseCollector(check, [tables, views], ["db1", "db2"])

    assert collector.collect_schemas() is True

    events = events_by_kind(aggregator)
    db1_tables = [e for e in events["test_databases"] if e["metadata"] and e["metadata"][0]["name"] == "db1"]
    assert [e["metadata"][0]["tables"][0]["name"] for e in db1_tables] == ["first"]
    assert "collection_payloads_count" not in db1_tables[0]
    assert snapshot_names(events["test_databases"]) == ["db2"]
    # Views run on db1 after tables failed there, and the terminal payload follows the two chunk payloads.
    assert [e.get("collection_payloads_count") for e in events["test_views"]] == [None, None, 3, None, 2]
    aggregator.assert_metric(
        f"dd.{check.dbms}.schema.tables_count", value=1, tags=check.tags + ["status:success", "kind:test_databases"]
    )


@pytest.mark.unit
def test_database_collector_unopenable_database_skips_all_kinds(aggregator: AggregatorStub):
    check = TestDatabaseCheck()
    rows = {"db1": ["a"], "db2": ["b"], "db3": ["c"]}
    tables = FakeTablesCollector(check, SchemaCollectorConfig(), rows)
    views = FakeViewsCollector(check, SchemaCollectorConfig(), rows)
    collector = FakeDatabaseCollector(check, [tables, views], ["db1", "db2", "db3"], unopenable=["db2"])

    assert collector.collect_schemas() is True

    events = events_by_kind(aggregator)
    assert snapshot_names(events["test_databases"]) == ["db1", "db3"]
    assert snapshot_names(events["test_views"]) == ["db1", "db3"]


@pytest.mark.unit
def test_database_collector_reports_telemetry_per_kind(aggregator: AggregatorStub):
    check = TestDatabaseCheck()
    rows = {"db1": ["a", "b"]}
    tables = FakeTablesCollector(check, SchemaCollectorConfig(), {"db1": ["a"]})
    views = FakeViewsCollector(check, SchemaCollectorConfig(), rows)
    FakeDatabaseCollector(check, [tables, views], ["db1"]).collect_schemas()

    table_tags = check.tags + ["status:success", "kind:test_databases"]
    view_tags = check.tags + ["status:success", "kind:test_views"]
    aggregator.assert_metric(f"dd.{check.dbms}.schema.tables_count", value=1, tags=table_tags, count=1)
    aggregator.assert_metric(f"dd.{check.dbms}.schema.views_count", value=2, tags=view_tags, count=1)
    for tags in (table_tags, view_tags):
        aggregator.assert_metric(f"dd.{check.dbms}.schema.time", tags=tags, count=1)
        aggregator.assert_metric(f"dd.{check.dbms}.schema.payloads_count", value=1, tags=tags, count=1)


@pytest.mark.unit
def test_database_collector_database_listing_failure_reports_error_for_every_kind(aggregator: AggregatorStub):
    check = TestDatabaseCheck()
    tables = FakeTablesCollector(check, SchemaCollectorConfig(), {})
    views = FakeViewsCollector(check, SchemaCollectorConfig(), {})
    collector = FakeDatabaseCollector(check, [tables, views], [])

    def fail() -> list[dict[str, Any]]:
        raise RuntimeError("cannot list databases")

    collector._get_databases = fail
    with pytest.raises(RuntimeError, match="cannot list databases"):
        collector.collect_schemas()

    for kind in ("test_databases", "test_views"):
        aggregator.assert_metric(f"dd.{check.dbms}.schema.time", tags=check.tags + ["status:error", f"kind:{kind}"])


@pytest.mark.unit
@pytest.mark.parametrize(
    "configured_chunk_size, expected_chunk_size",
    [
        pytest.param(10_000, 500, id="caps large table chunk size"),
        pytest.param(100, 100, id="keeps smaller configured size"),
    ],
)
def test_view_collector_payload_chunk_size(configured_chunk_size: int, expected_chunk_size: int):
    """View rows carry full definitions, so view payloads must not use the much larger table chunk size."""
    config = SchemaCollectorConfig()
    config.payload_chunk_size = configured_chunk_size
    views = FakeViewsCollector(TestDatabaseCheck(), config, {})

    assert views.payload_chunk_size == expected_chunk_size


@pytest.mark.unit
@pytest.mark.parametrize("tables_query_fails", [True, False], ids=["query fails", "query succeeds"])
def test_database_collector_stops_when_cancelled_during_collection(
    aggregator: AggregatorStub, tables_query_fails: bool
):
    """
    A cancel during one kind's query ends the run before the next kind or database starts. When the cancel also
    makes the query fail (such as a closed connection), the error is not skipped as a per-kind failure.
    """
    check = TestDatabaseCheck()
    rows = {"db1": ["a"], "db2": ["b"]}
    tables = FakeTablesCollector(check, SchemaCollectorConfig(), rows)
    views = FakeViewsCollector(check, SchemaCollectorConfig(), rows)
    collector = FakeDatabaseCollector(check, [tables, views], ["db1", "db2"])
    cancelled = False

    def raise_if_cancelled() -> None:
        if cancelled:
            raise RuntimeError("cancelled")

    def cancel_during_query(database_name: str) -> Iterator[str]:
        nonlocal cancelled
        cancelled = True
        if tables_query_fails:
            raise RuntimeError("connection closed")
        yield from rows[database_name]

    collector._raise_if_cancelled = raise_if_cancelled
    tables._iter_rows = cancel_during_query

    with pytest.raises(RuntimeError, match="cancelled"):
        collector.collect_schemas()

    assert [(s.database_name, s.queries) for s in collector.sessions] == [("db1", ["test_databases"])]
    aggregator.assert_metric(f"dd.{check.dbms}.schema.time", tags=check.tags + ["status:error", "kind:test_views"])
