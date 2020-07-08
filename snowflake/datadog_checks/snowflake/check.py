# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import closing
import snowflake.connector as sf

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.db import QueryManager

from . import queries
from .config import Config


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

        # Ensure we're only collecting metrics from last run
        self._last_ts = None

        # Add default tags like account to all metrics
        self._tags = self.config.tags + ['account:%s'.format(self.config.account)]

        if self.config.password:
            self.register_secret(self.config.password)

        self._query_manager = QueryManager(
            self,
            self.execute_query_raw,
            queries=[
                queries.StorageUsageMetrics,
                queries.CreditUsage,
                queries.WarehouseCreditUsage,
            ],
            tags=self._tags,
        )

        self.check_initializations.append(self._query_manager.compile_queries)

    def check(self, _):
        self.connect(self.config)
        self._query_manager.execute()
        self._collect_version()
        #val = self.execute_query_raw("select SERVICE_TYPE, NAME, CREDITS_USED_COMPUTE, CREDITS_USED_CLOUD_SERVICES, CREDITS_USED from METERING_HISTORY where start_time >= to_timestamp_ltz('2020-06-30 08:00:00.000 -0700');")
        #raise Exception(val)

    def execute_query_raw(self, query):
        with closing(self._conn.cursor()) as cursor:
            cursor.execute(query)
            if cursor.rowcount is None or cursor.rowcount < 1:
                self.log.warning("Failed to fetch records from query: `%s`.", query)
                return []
            return cursor.fetchall()

    def connect(self, config):
        if self._conn is not None:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=self._tags)
            return
        try:
            conn = sf.connect(
                user=self.config.user,
                password=self.config.password,
                account=self.config.account,
                database="SNOWFLAKE", # This integration only queries SNOWFLAKE DB and ACCOUNT_USAGE schema
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
            self.log.debug("Error collecting version for Snowflake: %s", e)

        if version:
            self.set_metadata('version', version)
