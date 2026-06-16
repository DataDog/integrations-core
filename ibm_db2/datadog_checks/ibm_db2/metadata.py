# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import time
from typing import Any

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method

from .schemas import DEFAULT_SCHEMAS_COLLECTION_INTERVAL, Db2SchemaCollector

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

DEFAULT_SETTINGS_COLLECTION_INTERVAL = 600

SETTINGS_QUERY = """\
SELECT *
FROM (
    SELECT
        NAME AS name,
        VALUE AS value,
        VALUE_FLAGS AS value_flags,
        DEFERRED_VALUE AS deferred_value,
        DEFERRED_VALUE_FLAGS AS deferred_value_flags,
        DATATYPE AS datatype,
        CAST(NULL AS INTEGER) AS member,
        'dbm' AS config_scope
    FROM SYSIBMADM.DBMCFG
    UNION ALL
    SELECT
        NAME AS name,
        VALUE AS value,
        VALUE_FLAGS AS value_flags,
        DEFERRED_VALUE AS deferred_value,
        DEFERRED_VALUE_FLAGS AS deferred_value_flags,
        DATATYPE AS datatype,
        MEMBER AS member,
        'db' AS config_scope
    FROM SYSIBMADM.DBCFG
    WHERE MEMBER = 0
) settings
{where_clause}
ORDER BY config_scope, name
"""


def agent_check_getter(dbm_job):
    return dbm_job._check


def _positive_float(value: Any, default: float) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


class Db2Metadata(DBMAsyncJob):
    """Collect Db2 DBM metadata."""

    def __init__(self, check, config) -> None:
        self.log = check.log
        self._check = check
        self._config = config
        settings_config = config.settings_config
        schemas_config = config.schemas_config
        self.settings_collection_interval = _positive_float(
            settings_config.get('collection_interval'), DEFAULT_SETTINGS_COLLECTION_INTERVAL
        )
        self.schemas_collection_interval = _positive_float(
            schemas_config.get('collection_interval'), DEFAULT_SCHEMAS_COLLECTION_INTERVAL
        )
        self._settings_enabled = config.dbm_enabled and is_affirmative(settings_config.get('enabled', True))
        self._schemas_enabled = config.dbm_enabled and is_affirmative(schemas_config.get('enabled', False))
        self._ignored_settings_patterns = list(settings_config.get('ignored_settings_patterns', []) or [])
        self._conn_key_prefix = 'dbm-metadata-'
        self._schema_collector = Db2SchemaCollector(check, config) if self._schemas_enabled else None
        self._last_settings_collection_time = 0
        self._last_schemas_collection_time = 0
        self.tags: list[str] = []
        self._tags_no_db: list[str] = []
        collection_interval = (
            min(
                interval
                for interval, enabled in (
                    (self.settings_collection_interval, self._settings_enabled),
                    (self.schemas_collection_interval, self._schemas_enabled),
                )
                if enabled
            )
            if self._settings_enabled or self._schemas_enabled
            else self.settings_collection_interval
        )

        super().__init__(
            check,
            run_sync=is_affirmative(settings_config.get('run_sync', schemas_config.get('run_sync', False))),
            enabled=self._settings_enabled or self._schemas_enabled,
            expected_db_exceptions=(),
            min_collection_interval=config.min_collection_interval,
            dbms='db2',
            rate_limit=1 / collection_interval,
            job_name='database-metadata',
            shutdown_callback=self._close_db_conn,
        )

    def _close_db_conn(self) -> None:
        self._check.connection.close(self._conn_key_prefix)

    def run_job(self) -> None:
        source_tags = self._tags or self._check.tag_manager.get_tags()
        self.tags = [tag for tag in source_tags if not tag.startswith('dd.internal')]
        self._tags_no_db = [tag for tag in self.tags if not tag.startswith('db:')]

        elapsed_time_settings = time.time() - self._last_settings_collection_time
        if self._settings_enabled and elapsed_time_settings >= self.settings_collection_interval:
            self._last_settings_collection_time = time.time()
            self.report_db2_settings()

        elapsed_time_schemas = time.time() - self._last_schemas_collection_time
        if self._schemas_enabled and elapsed_time_schemas >= self.schemas_collection_interval:
            self._last_schemas_collection_time = time.time()
            if self._schema_collector is not None:
                self._schema_collector.collect_schemas()

    @tracked_method(agent_check_getter=agent_check_getter)
    def report_db2_settings(self) -> None:
        settings = self._collect_settings()
        event = {
            'host': self._check.reported_hostname,
            'database_instance': self._check.database_identifier,
            'agent_version': datadog_agent.get_version(),
            'dbms': 'db2',
            'kind': 'db2_settings',
            'collection_interval': self.settings_collection_interval,
            'dbms_version': self._check.dbms_version,
            'tags': self._tags_no_db,
            'timestamp': time.time() * 1000,
            'cloud_metadata': self._check.cloud_metadata,
            'metadata': settings,
        }
        self._check.database_monitoring_metadata(json.dumps(event, default=default_json_event_encoding))

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _collect_settings(self) -> list[dict[str, Any]]:
        query, params = self._settings_query()
        rows, _ = self._check.connection.query(self._conn_key_prefix, query, params=params)
        return [self._normalize_setting(row) for row in rows]

    def _settings_query(self) -> tuple[str, list[str]]:
        if not self._ignored_settings_patterns:
            return SETTINGS_QUERY.format(where_clause=''), []

        where_clause = 'WHERE ' + ' AND '.join('name NOT LIKE ?' for _ in self._ignored_settings_patterns)
        return SETTINGS_QUERY.format(where_clause=where_clause), self._ignored_settings_patterns

    @staticmethod
    def _normalize_setting(row: dict[str, Any]) -> dict[str, Any]:
        setting = {str(key).lower(): value for key, value in row.items()}
        setting['pending_change'] = setting.get('value') != setting.get('deferred_value')
        return _strip_none_values(setting)


def _strip_none_values(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if value is not None}
