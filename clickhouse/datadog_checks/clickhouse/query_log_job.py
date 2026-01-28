# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Base class for jobs that query ClickHouse's system.query_log table.

This module provides shared functionality for:
- ClickhouseStatementMetrics (aggregated query metrics)
- ClickhouseQueryCompletions (individual query samples)

Both jobs share:
- Checkpoint-based collection with persistent cache
- Dedicated DB client management
- Internal user filtering
- Query obfuscation
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from clickhouse_connect.driver.exceptions import OperationalError

if TYPE_CHECKING:
    from datadog_checks.clickhouse import ClickhouseCheck

from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import DBMAsyncJob, obfuscate_sql_with_metadata
from datadog_checks.base.utils.serialization import json

# Query to get current timestamp from ClickHouse in microseconds
# Used for first run or when no rows are returned (to advance checkpoint during idle periods)
GET_CURRENT_TIME_QUERY = "SELECT toUnixTimestamp64Micro(now64(6))"

# List of internal Cloud users to exclude from query metrics/samples
# These are Datadog Cloud internal service accounts
INTERNAL_CLOUD_USERS = frozenset(
    {
        # Add internal Cloud user names here as needed
        # 'internal_service_user',
    }
)


def agent_check_getter(self):
    """Helper function for @tracked_method decorator to get the check instance."""
    return self._check


class ClickhouseQueryLogJob(DBMAsyncJob):
    """
    Base class for jobs that query system.query_log.

    Provides shared functionality:
    - Checkpoint-based collection (microsecond precision)
    - Dedicated DB client with connection pooling
    - Internal user filtering for Cloud deployments
    - Query obfuscation with metadata extraction

    Subclasses must implement:
    - CHECKPOINT_CACHE_KEY: class attribute for persistent cache key
    - _collect_and_submit(): main collection logic
    """

    # Subclasses must override this with their specific cache key
    CHECKPOINT_CACHE_KEY: str = ""

    def __init__(
        self,
        check: ClickhouseCheck,
        config,
        job_name: str,
    ):
        """
        Initialize the query log job.

        Args:
            check: The parent ClickhouseCheck instance
            config: Job-specific configuration object
            job_name: Name for this job (e.g., "query-metrics", "query-completions")
        """
        collection_interval = float(config.collection_interval)
        super().__init__(
            check,
            run_sync=config.run_sync,
            enabled=config.enabled,
            expected_db_exceptions=(Exception,),
            min_collection_interval=check.check_interval if hasattr(check, 'check_interval') else 15,
            dbms="clickhouse",
            rate_limit=1 / float(collection_interval),
            job_name=job_name,
        )
        self._check = check
        self._collection_interval = collection_interval
        self._config = config

        # Tags (set in run_job before collection)
        self._tags_no_db = None
        self.tags = None

        # Dedicated client for this job (uses shared connection pool)
        self._db_client = None

        # Checkpoint state for exactly-once collection semantics
        # Will be loaded from persistent cache on first collection
        self._last_checkpoint_microseconds = None
        self._current_checkpoint_microseconds = None

        # Obfuscator options (shared across all query log jobs)
        obfuscate_options = {
            'return_json_metadata': True,
            'collect_tables': True,
            'collect_commands': True,
            'collect_comments': True,
        }
        self._obfuscate_options = to_native_string(json.dumps(obfuscate_options))

    def cancel(self):
        """Cancel the job and clean up the dedicated client."""
        super().cancel()
        self._close_db_client()

    def _close_db_client(self):
        """Close the dedicated database client if it exists."""
        if self._db_client:
            try:
                self._db_client.close()
            except Exception as e:
                self._log.debug("Error closing DBM client: %s", e)
            self._db_client = None

    def _execute_query(self, query: str):
        """
        Execute a query using the dedicated client (with shared connection pool).

        Args:
            query: SQL query to execute

        Returns:
            List of result rows

        Raises:
            Exception: If job is cancelled or query fails
        """
        if self._cancel_event.is_set():
            raise Exception("Job loop cancelled. Aborting query.")
        try:
            if self._db_client is None:
                self._db_client = self._check.create_dbm_client()
            result = self._db_client.query(query)
            return result.result_rows
        except OperationalError as e:
            # Connection-related error - reset client to force reconnect
            self._log.warning("Connection error, will reconnect: %s", e)
            self._close_db_client()
            raise
        except Exception as e:
            # Query error (syntax, timeout, etc.) - don't reset connection
            self._log.warning("Query error: %s", e)
            raise

    def _get_current_time_from_db(self) -> int:
        """
        Get the current timestamp from ClickHouse in microseconds.
        Using the database's clock avoids drift between agent and database time.

        Returns:
            Current timestamp in microseconds (Unix epoch)
        """
        result = self._execute_query(GET_CURRENT_TIME_QUERY)
        if result and len(result) > 0:
            return int(result[0][0])
        raise Exception("Failed to get current time from ClickHouse")

    def _get_last_checkpoint(self) -> int:
        """
        Get the last checkpoint for collection.

        Returns:
            Last checkpoint in microseconds

        Logic:
            - First run: Fetches current time from DB and subtracts collection_interval
            - Subsequent runs: Returns last saved checkpoint from persistent cache
        """
        try:
            # Attempt to read from persistent cache
            cached_value = self._check.read_persistent_cache(self.CHECKPOINT_CACHE_KEY)
            if cached_value:
                checkpoint = int(cached_value)
                self._log.debug("Loaded checkpoint from persistent cache: %d microseconds", checkpoint)
                return checkpoint
        except Exception as e:
            self._log.warning(
                "Could not load checkpoint from persistent cache: %s. Will use default lookback window.", str(e)
            )

        # First run or cache error - fetch current time and create lookback window
        current_time_micros = self._get_current_time_from_db()
        default_checkpoint = current_time_micros - int(self._collection_interval * 1_000_000)

        self._log.info(
            "First collection run. Starting from %d (lookback=%ds)",
            default_checkpoint,
            int(self._collection_interval),
        )
        return default_checkpoint

    def _save_checkpoint(self, timestamp_microseconds: int):
        """
        Save the current collection timestamp to persistent cache.

        Args:
            timestamp_microseconds: The checkpoint timestamp to save

        Note:
            - Only called AFTER successful sample submission
            - Failures are logged but don't raise exceptions
            - Next collection will retry with previous checkpoint
        """
        try:
            self._check.write_persistent_cache(self.CHECKPOINT_CACHE_KEY, str(timestamp_microseconds))
            self._log.debug("Saved checkpoint to persistent cache: %d microseconds", timestamp_microseconds)
        except Exception as e:
            self._log.error(
                "Failed to save checkpoint to persistent cache: %s. Next collection will retry the same time window.",
                str(e),
            )

    def _get_internal_user_filter(self) -> str:
        """
        Build the SQL filter to exclude internal Cloud users.

        Returns:
            SQL fragment starting with "AND " to exclude internal users
        """
        filters = ["user NOT LIKE '%-internal'"]
        if INTERNAL_CLOUD_USERS:
            users_list = ", ".join(f"'{user}'" for user in INTERNAL_CLOUD_USERS)
            filters.append(f"user NOT IN ({users_list})")
        return "AND " + " AND ".join(filters)

    def _obfuscate_query(self, query_text: str) -> dict | None:
        """
        Obfuscate a SQL query and extract metadata.

        Args:
            query_text: Raw SQL query text

        Returns:
            Dict with 'query' (obfuscated), 'query_signature', and metadata keys,
            or None if obfuscation failed
        """
        try:
            statement = obfuscate_sql_with_metadata(query_text, self._obfuscate_options)
            obfuscated_query = statement['query']
            metadata = statement['metadata']

            return {
                'query': obfuscated_query,
                'query_signature': compute_sql_signature(obfuscated_query),
                'dd_tables': metadata.get('tables'),
                'dd_commands': metadata.get('commands'),
                'dd_comments': metadata.get('comments'),
            }
        except Exception as e:
            self._log.debug("Failed to obfuscate query | err=[%s]", e)
            self._check.count(
                "dd.clickhouse.query_log_job.error",
                1,
                tags=self.tags + ["error:obfuscate-query"],
                raw=True,
            )
            return None

    @staticmethod
    def to_microseconds(val) -> int:
        """
        Convert a datetime or int value to microseconds.

        ClickHouse Cloud returns datetime objects while self-hosted returns integers.

        Args:
            val: Datetime object or integer timestamp

        Returns:
            Timestamp in microseconds
        """
        if val is None:
            return 0
        if hasattr(val, 'timestamp'):  # datetime object
            return int(val.timestamp() * 1_000_000)
        return int(val)

    @property
    def deployment_mode(self) -> str:
        """
        Get a human-readable string describing the deployment mode.

        Returns:
            'cluster-wide (single endpoint)' for ClickHouse Cloud
            'local (direct)' for self-hosted
        """
        return "cluster-wide (single endpoint)" if self._check.is_single_endpoint_mode else "local (direct)"

    def _advance_checkpoint(self):
        """
        Save the current checkpoint and update the last checkpoint reference.

        This should be called ONLY after successful submission to ensure
        exactly-once semantics. If submission fails, don't call this method
        so the same time window will be retried.
        """
        if self._current_checkpoint_microseconds:
            self._save_checkpoint(self._current_checkpoint_microseconds)
            self._last_checkpoint_microseconds = self._current_checkpoint_microseconds

    def _set_checkpoint_from_event_time(self, max_event_time: int):
        """
        Set the current checkpoint from the max event time in results.

        If no results (max_event_time == 0), fetches current time from DB
        to advance the checkpoint during idle periods.

        Args:
            max_event_time: Maximum event_time_microseconds from query results
        """
        if max_event_time > 0:
            self._current_checkpoint_microseconds = max_event_time
            self._log.debug("Checkpoint from results: %d", max_event_time)
        else:
            # No rows returned - fetch current time to advance checkpoint
            # This prevents re-querying the same empty window indefinitely
            self._current_checkpoint_microseconds = self._get_current_time_from_db()
            self._log.debug("No rows, fetched checkpoint from DB: %d", self._current_checkpoint_microseconds)

    def run_job(self):
        """
        Main job entry point. Sets up tags and calls subclass collection logic.
        """
        # Do not emit any dd.internal metrics for DBM specific check code
        self.tags = [t for t in self._tags if not t.startswith('dd.internal')]
        self._tags_no_db = [t for t in self.tags if not t.startswith('db:')]
        self._collect_and_submit()

    @abstractmethod
    def _collect_and_submit(self):
        """
        Collect data from query_log and submit to Datadog.

        Subclasses must implement this method with their specific:
        - Query execution
        - Data processing
        - Payload creation
        - Submission via appropriate database_monitoring_* method
        """
        pass
