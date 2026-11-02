# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""
DBM schema collection.

A collection run is split into two parts:

- `SchemaObjectCollector` collects one kind of catalog object, such as tables or views. It owns that kind's
  query, row mapping, payload buffer, and telemetry, and every payload it sends carries its own `kind`.
- `DatabaseSchemaCollector` owns database discovery and the per-database connection. It lists the databases once,
  opens each database once, and runs every object collector on that open database in turn.

`SchemaCollector` is the original single-kind collector, where one class does both jobs.
"""

from __future__ import annotations

import contextlib
from abc import ABC, abstractmethod
from collections.abc import Iterator, Sequence
from typing import TYPE_CHECKING, Any, ContextManager, TypedDict

from datadog_checks.base.utils.serialization import json

from .utils import TagManager, now_ms

if TYPE_CHECKING:
    from datadog_checks.base.checks.db import DatabaseCheck

try:
    import datadog_agent  # type: ignore
except ImportError:
    from datadog_checks.base.stubs import datadog_agent


class DatabaseInfo(TypedDict):
    name: str


# The schema collector sends lists of DatabaseObjects to the agent
# DBMS subclasses may add additional fields to the dictionary
class DatabaseObject(TypedDict):
    name: str


# Common configuration for schema collector
# Individual DBMS implementations should map their specific
# configuration to this type
class SchemaCollectorConfig:
    def __init__(self):
        self.collection_interval = 3600
        self.payload_chunk_size = 10_000


class SchemaObjectCollector(ABC):
    """
    Collects one kind of catalog object and sends it as DBM metadata payloads of that kind.

    Payloads are snapshotted per database: every payload of one database's collection carries the same
    `collection_started_at`, and the last one carries `collection_payloads_count`.
    """

    def __init__(self, check: DatabaseCheck, config: SchemaCollectorConfig):
        self._check = check
        self._log = check.log
        self._config = config
        self._reset()

    def _reset(self):
        # Timestamp in whole milliseconds when the current database's collection started.
        self._collection_started_at = None
        self._collection_payloads_count = 0
        self._queued_rows = []
        # Totals for the current run, reported as telemetry when the run ends.
        self._total_rows_count = 0
        self._total_payloads_count = 0
        self._collection_time_ms = 0

    @property
    @abstractmethod
    def kind(self) -> str:
        """
        Returns the kind property of the schema metadata event.
        Subclasses should override this property to return the kind of schema being collected.
        """
        raise NotImplementedError("Subclasses must implement kind")

    @property
    def object_count_metric_name(self) -> str:
        return f"dd.{self._check.dbms}.schema.tables_count"

    @property
    def payload_chunk_size(self) -> int:
        """The number of rows that triggers sending a payload before the database's collection ends."""
        return self._config.payload_chunk_size

    @abstractmethod
    def _open_rows(self, session: Any, database_name: str) -> ContextManager[Iterator[Any]]:
        """
        Runs this kind's catalog query for one database and yields an iterator over its rows.

        `session` is whatever `DatabaseSchemaCollector._open_database` yielded for this database. The rows must be
        fully read, or the query closed, when the context exits, because the next kind runs on the same session.
        """

    def _map_row(self, database: DatabaseInfo, _cursor_row) -> DatabaseObject:
        """
        Maps a cursor row to a dict that matches the schema expected by DBM.
        The base implementation of this method returns just the database dictionary.
        Subclasses should override this method to add schema and table data based on the cursor row.
        """
        return {**database}

    def _collect_database(self, session: Any, database: DatabaseInfo) -> None:
        """
        Collects and sends this kind's objects for one database.

        If collection fails partway through, the payloads already sent stay sent and the database's snapshot never
        gets its terminal payload, so the backend treats that snapshot as incomplete. The error is re-raised.
        """
        started_at = now_ms()
        self._collection_started_at = started_at
        self._collection_payloads_count = 0
        self._queued_rows = []
        rows_count = 0
        try:
            with self._open_rows(session, database['name']) as rows:
                for row in rows:
                    self._queued_rows.append(self._map_row(database, row))
                    rows_count += 1
                    self.maybe_flush(is_last_payload=False)
            self.maybe_flush(is_last_payload=True)
            self._total_rows_count += rows_count
            self._log.debug(
                "Completed %s collection for database %s (%d rows, %d payloads)",
                self.kind,
                database['name'],
                rows_count,
                self._collection_payloads_count,
            )
        except Exception:
            self._queued_rows = []
            raise
        finally:
            self._total_payloads_count += self._collection_payloads_count
            self._collection_time_ms += now_ms() - started_at

    def _submit_telemetry(self, status: str) -> None:
        """Reports this kind's totals for the run that just ended, then clears them for the next run."""
        try:
            telemetry_tags = self._check.tags + ["status:" + status, "kind:" + self.kind]
            self._check.histogram(
                f"dd.{self._check.dbms}.schema.time",
                self._collection_time_ms,
                tags=telemetry_tags,
                hostname=self._check.reported_hostname,
                raw=True,
            )
            self._check.gauge(
                self.object_count_metric_name,
                self._total_rows_count,
                tags=telemetry_tags,
                hostname=self._check.reported_hostname,
                raw=True,
            )
            self._check.gauge(
                f"dd.{self._check.dbms}.schema.payloads_count",
                self._total_payloads_count,
                tags=telemetry_tags,
                hostname=self._check.reported_hostname,
                raw=True,
            )
        finally:
            self._reset()

    @property
    def base_event(self):
        return {
            "host": self._check.reported_hostname,
            "database_instance": self._check.database_identifier,
            "kind": self.kind,
            "agent_version": datadog_agent.get_version(),
            "collection_interval": self._config.collection_interval,
            "dbms": self._check.dbms,
            "dbms_version": str(self._check.dbms_version),
            "tags": self._event_tags(),
            "cloud_metadata": self._check.cloud_metadata,
            "collection_started_at": self._collection_started_at,
        }

    def _event_tags(self) -> list[str]:
        tag_manager = getattr(self._check, "tag_manager", None)
        if not isinstance(tag_manager, TagManager):
            return self._check.tags
        return tag_manager.get_tags(include_internal=False, include_db=False)

    def maybe_flush(self, is_last_payload):
        if is_last_payload or len(self._queued_rows) >= self.payload_chunk_size:
            event = self.base_event
            event["timestamp"] = now_ms()
            # DBM backend expects metadata to be an array of database objects
            event["metadata"] = self._queued_rows
            self._collection_payloads_count += 1
            if is_last_payload:
                # For the last payload, we need to include the total number of payloads collected
                # This is used for snapshotting to ensure that all payloads have been received
                event["collection_payloads_count"] = self._collection_payloads_count
            self._check.database_monitoring_metadata(json.dumps(event))

            self._queued_rows = []


class DatabaseSchemaCollector(ABC):
    """
    Runs several object collectors in one pass over the databases.

    Databases are listed once per run and each database is opened once, then every object collector runs on it in
    order. A failure in one object collector skips only that kind for that database; a failure to open the database
    skips every kind for it.

    The object collectors are scheduled together, so they share one collection interval.
    """

    def __init__(self, check: DatabaseCheck, object_collectors: Sequence[SchemaObjectCollector]):
        self._log = check.log
        self._object_collectors = list(object_collectors)

    @abstractmethod
    def _get_databases(self) -> list[DatabaseInfo]:
        """
        Returns a list of database dictionaries.
        Subclasses should override this method to return the list of databases to collect schema metadata for.
        """
        raise NotImplementedError("Subclasses must implement _get_databases")

    def _open_database(self, database_name: str) -> ContextManager[Any]:
        """
        Opens one database for collection and yields a session that every object collector receives.

        The default yields `None`, for object collectors that manage their own connection.
        """
        return contextlib.nullcontext()

    def collect_schemas(self) -> bool:
        """
        Collects and submits all applicable schema metadata to the agent.
        This class relies on the owning check to handle scheduling this method.

        Errors for a single database are logged and skipped. Any other error, including one raised while iterating
        the database list, ends the run with `status:error` telemetry and is re-raised.
        """
        status = "success"
        try:
            databases = self._get_databases()
            self._log.debug("Collecting schemas for %d databases", len(databases))
            for database in databases:
                database_name = database.get('name')
                if not database_name:
                    self._log.warning("database has no name: %s", database)
                    continue
                self._collect_database(database)
        except Exception as e:
            status = "error"
            self._log.error("Error collecting schema: %s", e)
            raise e
        finally:
            for object_collector in self._object_collectors:
                object_collector._submit_telemetry(status)
        return True

    def _collect_database(self, database: DatabaseInfo) -> None:
        database_name = database['name']
        self._log.debug("Starting collection of schemas for database %s", database_name)
        try:
            with self._open_database(database_name) as session:
                for object_collector in self._object_collectors:
                    try:
                        object_collector._collect_database(session, database)
                    except Exception as e:
                        self._log.warning(
                            "Skipping %s collection for database %s due to error: %s",
                            object_collector.kind,
                            database_name,
                            e,
                            exc_info=True,
                        )
        except Exception as e:
            self._log.warning("Skipping database %s due to error: %s", database_name, e, exc_info=True)


class SchemaCollector(SchemaObjectCollector):
    """
    Collects a single kind of catalog object, listing and opening databases itself.

    Subclasses implement `_get_databases`, `_get_cursor`, and `_get_next`. To collect several kinds on one
    connection per database, use `DatabaseSchemaCollector` with one `SchemaObjectCollector` per kind instead.
    """

    def collect_schemas(self) -> bool:
        """
        Collects and submits all applicable schema metadata to the agent.
        This class relies on the owning check to handle scheduling this method.
        """
        return SingleKindSchemaCollector(self).collect_schemas()

    @abstractmethod
    def _get_databases(self) -> list[DatabaseInfo]:
        """
        Returns a list of database dictionaries.
        Subclasses should override this method to return the list of databases to collect schema metadata for.
        """
        raise NotImplementedError("Subclasses must implement _get_databases")

    @abstractmethod
    def _get_cursor(self, database):
        """
        Returns a cursor for the given database.
        Subclasses should override this method to return the cursor for the given database.
        """
        raise NotImplementedError("Subclasses must implement _get_cursor")

    @abstractmethod
    def _get_next(self, cursor):
        """
        Returns the next row from the cursor.
        Subclasses should override this method to return the next row from the cursor.
        """
        raise NotImplementedError("Subclasses must implement _get_next")

    @contextlib.contextmanager
    def _open_rows(self, _session: Any, database_name: str) -> Iterator[Iterator[Any]]:
        with self._get_cursor(database_name) as cursor:
            yield self._iter_cursor(cursor)

    def _iter_cursor(self, cursor) -> Iterator[Any]:
        # A falsy row ends the cursor, as `_get_next` has always been allowed to signal.
        while row := self._get_next(cursor):
            yield row


class SingleKindSchemaCollector(DatabaseSchemaCollector):
    """Runs a `SchemaCollector`, which opens its own cursor per database, as the only object collector."""

    def __init__(self, collector: SchemaCollector):
        super().__init__(collector._check, [collector])
        self._collector = collector

    def _get_databases(self) -> list[DatabaseInfo]:
        return self._collector._get_databases()


DEFAULT_MAX_VIEWS = 1000
# Each view row carries its full definition, so view payloads use far smaller chunks than tables.
VIEW_PAYLOAD_CHUNK_SIZE = 500


class ViewColumn(TypedDict):
    """A column a view projects, in the shape table columns use. DBMS implementations may add fields."""

    name: str
    data_type: str
    nullable: bool


class ViewObject(TypedDict):
    """A view in a `<dbms>_views` payload. DBMS implementations may add fields, such as an ID or owner."""

    name: str
    definition: str | None
    columns: list[ViewColumn]


class ViewObjectCollector(SchemaObjectCollector):
    """
    Collects views as a separate `<dbms>_views` payload kind.

    View payloads keep the table payload's nesting, so a DBMS that groups tables under schemas also emits each view
    under its schema, next to an empty `tables` list. Use `_schema_with_view` to build that wrapper.
    """

    @property
    def object_count_metric_name(self) -> str:
        return f"dd.{self._check.dbms}.schema.views_count"

    @property
    def payload_chunk_size(self) -> int:
        return min(self._config.payload_chunk_size, VIEW_PAYLOAD_CHUNK_SIZE)

    @staticmethod
    def _schema_with_view(schema: dict[str, Any], view: ViewObject) -> dict[str, Any]:
        """Returns a schema object holding one view and no tables."""
        return {**schema, "tables": [], "views": [view]}
