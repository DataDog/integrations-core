# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import psycopg

from datadog_checks.base.utils.db.utils import DBMAsyncJob

if TYPE_CHECKING:
    from datadog_checks.postgres import PostgreSql
    from datadog_checks.postgres.config_models.instance import InstanceConfig


class PostgresDataObservability(DBMAsyncJob):
    def __init__(self, check: PostgreSql, config: InstanceConfig):
        self._check = check
        self._config = config.data_observability
        super(PostgresDataObservability, self).__init__(
            check,
            rate_limit=1 / float(self._config.collection_interval),
            run_sync=self._config.run_sync,
            enabled=self._config.enabled,
            dbms="postgres",
            min_collection_interval=config.collection_interval,
            expected_db_exceptions=(psycopg.errors.DatabaseError,),
            job_name="data-observability",
        )

    def run_job(self):
        # Put your data observability logic here
        # This should be called at the collection interval
        pass
