# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import snowflake.connector as sf

from datadog_checks.base import AgentCheck
from .config import Config


class SnowflakeCheck(AgentCheck):
    """
    Collect Snowflake account usage metrics
    """

    SERVICE_CHECK_CONNECT = 'snowflake.can_connect'

    def __init__(self, *args, **kwargs):
        super(SnowflakeCheck, self).__init__(*args, **kwargs)
        self.config = Config(self.instance)
        self._conn = None

        # Add default tags like account to all metrics
        self._tags = self.config.tags + ['account:%s'.format(self.config.account)]

        if self.config.password:
            self.register_secret(self.config.password)


    def check(self, _):
        # Connect
        self.connect(self.config)
        cur = self._conn.cursor()
        cur.execute("""
                    select count(*) as number_of_jobs
            from query_history
            where start_time >= date_trunc(month, current_date);""")
        raise Exception(cur.fetchone()[0])

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
