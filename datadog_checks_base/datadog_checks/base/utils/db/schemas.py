# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, TypedDict

import orjson as json

from .utils import now_ms

if TYPE_CHECKING:
    from datadog_checks.base.checks.db import DatabaseCheck

try:
    import datadog_agent
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
        self.enabled = False
        self.payload_chunk_size = 10_000


class SchemaCollector(ABC):
    """
    Abstract base class for DBM schema collectors.

    Attributes:
        _collection_started_at (int): Timestamp in whole milliseconds
            when the current collection started.
    """

    _collection_started_at: int | None = None

    def __init__(self, check: DatabaseCheck, config: SchemaCollectorConfig):
        self._check = check
        self._log = check.log
        self._config = config
        self._dbms = check.__class__.__name__.lower()
        if self._dbms == 'postgresql':
            # Backwards compatibility for metrics namespacing
            self._dbms = 'postgres'
        self._reset()

    def _reset(self):
        self._collection_started_at = None
        self._collection_payloads_count = 0
        self._queued_rows = []
        self._total_rows_count = 0

    def collect_schemas(self) -> bool:
        """
        Collects and submits all applicable schema metadata to the agent.
        This class relies on the owning check to handle scheduling this method.

        This method will enforce non-overlapping invocations and
        returns False if the previous collection was still in progress when invoked again.
        """
        if self._collection_started_at is not None:
            return False
        status = "success"
        try:
            self._collection_started_at = now_ms()
            databases = self._get_databases()
            for database in databases:
                database_name = database['name']
                if not database_name:
                    self._log.warning("database has no name %v", database)
                    continue
                with self._get_cursor(database_name) as cursor:
                    # Get the next row from the cursor
                    next = self._get_next(cursor)
                    while next:
                        self._queued_rows.append(self._map_row(database, next))
                        self._total_rows_count += 1
                        # Because we're iterating over a cursor we need to try to get
                        # the next row to see if we've reached the last row
                        next = self._get_next(cursor)
                        is_last_payload = database is databases[-1] and next is None
                        self.maybe_flush(is_last_payload)
        except Exception as e:
            status = "error"
            self._log.error("Error collecting schema: %s", e)
            raise e
        finally:
            self._check.histogram(
                f"dd.{self._dbms}.schema.time",
                now_ms() - self._collection_started_at,
                tags=self._check.tags + ["status:" + status],
                hostname=self._check.reported_hostname,
                raw=True,
            )
            self._check.gauge(
                f"dd.{self._dbms}.schema.tables_count",
                self._total_rows_count,
                tags=self._check.tags + ["status:" + status],
                hostname=self._check.reported_hostname,
                raw=True,
            )
            self._check.gauge(
                f"dd.{self._dbms}.schema.payloads_count",
                self._collection_payloads_count,
                tags=self._check.tags + ["status:" + status],
                hostname=self._check.reported_hostname,
                raw=True,
            )

            self._reset()
        return True

    @property
    def base_event(self):
        return {
            "host": self._check.reported_hostname,
            "database_instance": self._check.database_identifier,
            "kind": self.kind,
            "agent_version": datadog_agent.get_version(),
            "collection_interval": self._config.collection_interval,
            "dbms_version": str(self._check.dbms_version),
            "tags": self._check.tags,
            "cloud_metadata": self._check.cloud_metadata,
            "collection_started_at": self._collection_started_at,
        }

    def maybe_flush(self, is_last_payload):
        if is_last_payload or len(self._queued_rows) >= self._config.payload_chunk_size:
            event = self.base_event.copy()
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

    @property
    @abstractmethod
    def kind(self) -> str:
        """
        Returns the kind property of the schema metadata event.
        Subclasses should override this property to return the kind of schema being collected.
        """
        raise NotImplementedError("Subclasses must implement kind")

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

    def _map_row(self, database: DatabaseInfo, _cursor_row) -> DatabaseObject:
        """
        Maps a cursor row to a dict that matches the schema expected by DBM.
        The base implementation of this method returns just the database dictionary.
        Subclasses should override this method to add schema and table data based on the cursor row.
        """
        return {**database}
