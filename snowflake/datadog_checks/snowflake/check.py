# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
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
            self.execute_query,
            queries=[queries.StorageUsageMetrics],
            tags=self._tags,
        )

        self.check_initializations.append(self._query_manager.compile_queries)


    def check(self, _):
        # Connect
        self.connect(self.config)
        self._query_manager.execute()
        #val = self.execute_query("select storage_bytes, stage_bytes, failsafe_bytes from STORAGE_USAGE order by usage_date desc limit 1;")
        #raise Exception(val.fetchone()[0])


    def execute_query(self, query):
        cursor = self._conn.cursor()
        return cursor.execute(query)

    def connect(self, config):
        if self._conn is not None:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=self._tags)
            return
        try:
            conn = sf.connect(
                user = self.config.user,
                password = self.config.password,
                account = self.config.account,
                database = "SNOWFLAKE", # This integration only queries SNOWFLAKE DB and ACCOUNT_USAGE schema
                schema = "ACCOUNT_USAGE",
                warehouse= self.config.warehouse,
                role = self.config.role,
                passcode_in_password = self.config.passcode_in_password,
                passcode = self.config.passcode,
                client_prefetch_threads = self.config.client_prefetch_threads,
                login_timeout = self.config.login_timeout,
                ocsp_response_cache_filename = self.config.ocsp_response_cache_filename,
            )
        except Exception as e:
            msg = "Unable to connect to Snowflake: {}".format(e)
            self.service_check(self.SERVICE_CHECK_CONNECT, self.CRITICAL, message=msg, tags=self._tags)
        else:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=self._tags)
            self._conn = conn
