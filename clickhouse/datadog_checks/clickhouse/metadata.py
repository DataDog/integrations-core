# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

from clickhouse_connect.driver.exceptions import DatabaseError

if TYPE_CHECKING:
    from datadog_checks.clickhouse import ClickhouseCheck

from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.base.utils.tracking import tracked_method

from .schemas import ClickhouseSchemaCollector


def agent_check_getter(self):
    return self._check


class ClickhouseMetadata(DBMAsyncJob):
    """Top-level DBM job that drives the schema collector on its configured cadence."""

    def __init__(self, check: ClickhouseCheck):
        collection_interval = check._config.collect_schemas.collection_interval
        super(ClickhouseMetadata, self).__init__(
            check,
            rate_limit=1 / collection_interval,
            run_sync=check._config.collect_schemas.run_sync,
            enabled=check._config.collect_schemas.enabled,
            dbms=check.dbms,
            min_collection_interval=check._config.min_collection_interval,
            expected_db_exceptions=(DatabaseError,),
            job_name='clickhouse-metadata',
        )
        self._check = check
        self._collection_interval = collection_interval
        self._schema_collector = ClickhouseSchemaCollector(check)
        self._schema_collector._cancel_event = self._cancel_event

    def cancel(self):
        super(ClickhouseMetadata, self).cancel()
        self._schema_collector.close()

    @tracked_method(agent_check_getter=agent_check_getter)
    def run_job(self):
        try:
            self._schema_collector.collect_schemas()
        except Exception:
            self._log.exception("Schema collection failed")
