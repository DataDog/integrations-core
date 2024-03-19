# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import closing

import snowflake.connector as sf

from datadog_checks.base import AgentCheck, ConfigurationError, ensure_bytes, to_native_string
from datadog_checks.base.utils.db import QueryManager

from . import queries
from .config import Config

ACCOUNT_USAGE_METRIC_GROUPS = {
    'snowflake.query': [queries.WarehouseLoad, queries.QueryHistory],
    'snowflake.billing': [queries.CreditUsage, queries.WarehouseCreditUsage],
    'snowflake.storage': [queries.StorageUsageMetrics],
    'snowflake.storage.database': [queries.DatabaseStorageMetrics],
    'snowflake.storage.table': [queries.TableStorage],
    'snowflake.logins': [queries.LoginMetrics],
    'snowflake.data_transfer': [queries.DataTransferHistory],
    'snowflake.auto_recluster': [queries.AutoReclusterHistory],
    'snowflake.pipe': [queries.PipeHistory],
    'snowflake.replication': [queries.ReplicationUsage],
}

ORGANIZATION_USAGE_METRIC_GROUPS = {
    'snowflake.organization.contracts': [queries.OrgContractItems],
    'snowflake.organization.credit': [queries.OrgCreditUsage],
    'snowflake.organization.currency': [queries.OrgCurrencyUsage],
    'snowflake.organization.warehouse': [queries.OrgWarehouseCreditUsage],
    'snowflake.organization.storage': [queries.OrgStorageDaily],
    'snowflake.organization.balance': [queries.OrgBalance],
    'snowflake.organization.rate': [queries.OrgRateSheet],
    'snowflake.organization.data_transfer': [queries.OrgDataTransfer],
}


class SnowflakeCheck(AgentCheck):
    """
    Collect Snowflake account usage metrics
    """

    __NAMESPACE__ = 'snowflake'

    SERVICE_CHECK_CONNECT = 'can_connect'

    def __init__(self, *args, **kwargs):
        super(SnowflakeCheck, self).__init__(*args, **kwargs)
        self._config = Config(self.instance)
        self._conn = None

        self.proxy_host = self.init_config.get('proxy_host', None)
        self.proxy_port = self.init_config.get('proxy_port', None)
        self.proxy_user = self.init_config.get('proxy_user', None)
        self.proxy_password = self.init_config.get('proxy_password', None)

        # Add default tags like account to all metrics
        self._tags = self._config.tags + ['account:{}'.format(self._config.account)]

        if self._config.password:
            self.register_secret(self._config.password)

        if self._config.private_key_password:
            self.register_secret(self._config.private_key_password)

        if self._config.role == 'ACCOUNTADMIN':
            self.log.info(
                'Snowflake `role` is set as `ACCOUNTADMIN` which should be used cautiously, '
                'refer to docs about custom roles.'
            )
        metric_groups = (
            ORGANIZATION_USAGE_METRIC_GROUPS
            if (self._config.schema == 'ORGANIZATION_USAGE')
            else ACCOUNT_USAGE_METRIC_GROUPS
        )
        self.metric_queries = []
        self.errors = []

        # Collect queries corresponding to groups provided in the config
        for mgroup in self._config.metric_groups:
            try:
                self.metric_queries.extend(metric_groups[mgroup])
            except KeyError:
                self.errors.append(mgroup)
                continue

        if not self._config.aggregate_last_24_hours:
            # Modify queries to use legacy time aggregation behavior
            self.metric_queries = [
                {
                    **query,
                    'query': query['query'].replace(
                        'DATEADD(hour, -24, current_timestamp())', 'date_trunc(day, current_date)'
                    ),
                }
                for query in self.metric_queries
            ]

        if self.errors:
            self.log.warning(
                'Invalid metric_groups for `%s` found in snowflake conf.yaml: %s',
                self._config.schema,
                (', '.join(self.errors)),
            )
        if not self.metric_queries and not self._config.custom_queries_defined:
            raise ConfigurationError(
                'No valid metric_groups for `{}` or custom query configured, please list at least one.'.format(
                    self._config.schema
                )
            )

        self._query_manager = QueryManager(self, self.execute_query_raw, queries=self.metric_queries, tags=self._tags)
        self.check_initializations.append(self._query_manager.compile_queries)

    def read_token(self):
        if self._config.token_path:
            self.log.debug("Renewing Snowflake client token")
            with open(self._config.token_path, 'r', encoding="UTF-8") as f:
                self._config.token = f.read()

        return self._config.token

    def check(self, _):
        if self.instance.get('user'):
            self._log_deprecation('_config_renamed', 'user', 'username')

        self.connect()

        if self._conn is not None:
            # Execute queries
            self._query_manager.execute()

            self._collect_version()

            self.log.debug("Closing connection to Snowflake...")
            self._conn.close()

    def execute_query_raw(self, query):
        """
        Executes query with timestamp from parts if comparing start_time field.
        """
        with closing(self._conn.cursor()) as cursor:
            cursor.execute(query)

            if cursor.rowcount is None or cursor.rowcount < 1:
                self.log.debug("Failed to fetch records from query: `%s`", query)
                return
            # Iterating on the cursor provides one row at a time without loading all of them at once
            yield from cursor

    def connect(self):
        self.log.debug(
            "Establishing a new connection to Snowflake: account=%s, user=%s, database=%s, schema=%s, warehouse=%s, "
            "role=%s, timeout=%s, authenticator=%s, ocsp_response_cache_filename=%s, proxy_host=%s, proxy_port=%s",
            self._config.account,
            self._config.user,
            self._config.database,
            self._config.schema,
            self._config.warehouse,
            self._config.role,
            self._config.login_timeout,
            self._config.authenticator,
            self._config.ocsp_response_cache_filename,
            self.proxy_host,
            self.proxy_port,
        )

        try:
            conn = sf.connect(
                user=self._config.user,
                password=self._config.password,
                account=self._config.account,
                database=self._config.database,
                schema=self._config.schema,
                warehouse=self._config.warehouse,
                role=self._config.role,
                passcode_in_password=self._config.passcode_in_password,
                passcode=self._config.passcode,
                client_prefetch_threads=self._config.client_prefetch_threads,
                login_timeout=self._config.login_timeout,
                ocsp_response_cache_filename=self._config.ocsp_response_cache_filename,
                authenticator=self._config.authenticator,
                token=self.read_token(),
                private_key_file=self._config.private_key_path,
                private_key_file_pwd=ensure_bytes(self._config.private_key_password),
                client_session_keep_alive=self._config.client_keep_alive,
                proxy_host=self.proxy_host,
                proxy_port=self.proxy_port,
                proxy_user=self.proxy_user,
                proxy_password=self.proxy_password,
            )
        except Exception as e:
            msg = "Unable to connect to Snowflake: {}".format(e)
            self.service_check(self.SERVICE_CHECK_CONNECT, self.CRITICAL, message=msg, tags=self._tags)
            self.warning(msg)
        else:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=self._tags)
            self._conn = conn

    @AgentCheck.metadata_entrypoint
    def _collect_version(self):
        try:
            raw_version = next(self.execute_query_raw("select current_version();"))
            version = raw_version[0]
        except Exception as e:
            self.log.error("Error collecting version for Snowflake: %s", e)
        else:
            if version:
                self.set_metadata('version', version)

    # override
    def _normalize_tags_type(self, tags, device_name=None, metric_name=None):
        if self.disable_generic_tags:
            return super(SnowflakeCheck, self)._normalize_tags_type(tags, device_name, metric_name)

        # If disable_generic_tags is not enabled, for each generic tag we emmit both the generic and the non generic
        # version to ease transition.
        normalized_tags = []
        for tag in tags:
            if tag is not None:
                try:
                    tag = to_native_string(tag)
                except UnicodeError:
                    self.log.warning('Encoding error with tag `%s` for metric `%s`, ignoring tag', tag, metric_name)
                    continue
                normalized_tags.extend(list({tag, self.degeneralise_tag(tag)}))
        return normalized_tags
