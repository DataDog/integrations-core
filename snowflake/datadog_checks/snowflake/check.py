# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import closing

import snowflake.connector as sf

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.utils.db import QueryManager

from . import queries
from .config import Config

METRIC_GROUPS = {
    'snowflake.query': [queries.WarehouseLoad, queries.QueryHistory],
    'snowflake.billing': [queries.CreditUsage, queries.WarehouseCreditUsage],
    'snowflake.storage': [queries.StorageUsageMetrics, queries.DatabaseStorageMetrics],
    'snowflake.logins': [queries.LoginMetrics],
}


class SnowflakeCheck(AgentCheck):
    """
    Collect Snowflake account usage metrics
    """

    __NAMESPACE__ = 'snowflake'

    SERVICE_CHECK_CONNECT = 'snowflake.can_connect'

    def __init__(self, *args, **kwargs):
        super(SnowflakeCheck, self).__init__(*args, **kwargs)
        self.config = Config(self.instance)
        self._conn = None

        # Add default tags like account to all metrics
        self._tags = self.config.tags + ['account:{}'.format(self.config.account)]

        if self.config.password:
            self.register_secret(self.config.password)

        self.metric_queries = []
        self.errors = []
        for mgroup in self.config.metric_groups:
            try:
                self.metric_queries.extend(METRIC_GROUPS[mgroup])
            except KeyError:
                self.errors.append(mgroup)

        if self.errors:
            self.log.warning('Invalid metric_groups found in snowflake conf.yaml: %s', (', '.join(self.errors)))
        if not self.metric_queries:
            raise ConfigurationError('No valid metric_groups configured, please list at least one.')

        self._query_manager = QueryManager(self, self.execute_query_raw, queries=self.metric_queries, tags=self._tags)
        self.check_initializations.append(self._query_manager.compile_queries)

    def check(self, _):
        self.connect()

        # Execute queries
        self._query_manager.execute()

        self._collect_version()

    def execute_query_raw(self, query):
        """
        Executes query with timestamp from parts if comparing start_time field.
        """
        with closing(self._conn.cursor()) as cursor:
            cursor.execute(query)

            if cursor.rowcount is None or cursor.rowcount < 1:
                self.log.debug("Failed to fetch records from query: `%s`", query)
                return []
            return cursor.fetchall()

    def connect(self):
        if self._conn is not None:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=self._tags)
            return
        try:
            conn = sf.connect(
                user=self.config.user,
                password=self.config.password,
                account=self.config.account,
                database="SNOWFLAKE",  # This integration only queries SNOWFLAKE DB and ACCOUNT_USAGE schema
                schema="ACCOUNT_USAGE",
                warehouse=self.config.warehouse,
                role=self.config.role,
                passcode_in_password=self.config.passcode_in_password,
                passcode=self.config.passcode,
                client_prefetch_threads=self.config.client_prefetch_threads,
                login_timeout=self.config.login_timeout,
                ocsp_response_cache_filename=self.config.ocsp_response_cache_filename,
            )
        except Exception as e:
            msg = "Unable to connect to Snowflake: {}".format(e)
            self.service_check(self.SERVICE_CHECK_CONNECT, self.CRITICAL, message=msg, tags=self._tags)
        else:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=self._tags)
            self._conn = conn

    @AgentCheck.metadata_entrypoint
    def _collect_version(self):
        try:
            raw_version = self.execute_query_raw("select current_version();")
            version = raw_version[0][0]
        except Exception as e:
            self.log.error("Error collecting version for Snowflake: %s", e)
        else:
            if version:
                self.set_metadata('version', version)
