# (C) Datadog, Inc. 2013-present
# (C) Patrick Galbraith <patg@patg.net> 2013
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import division

import copy
import time
import traceback
from collections import defaultdict
from contextlib import closing, contextmanager
from string import Template
from typing import Any, Dict, List, Optional  # noqa: F401

import pymysql
from cachetools import TTLCache

<<<<<<< HEAD
from datadog_checks.base import AgentCheck, is_affirmative
from datadog_checks.base.checks.db import DatabaseCheck
=======
from datadog_checks.base import AgentCheck, DatabaseCheck, is_affirmative
>>>>>>> origin/master
from datadog_checks.base.utils.db import QueryExecutor, QueryManager
from datadog_checks.base.utils.db.health import HealthEvent, HealthStatus
from datadog_checks.base.utils.db.utils import (
    TagManager,
    default_json_event_encoding,
    tracked_query,
)
from datadog_checks.base.utils.db.utils import (
    resolve_db_host as agent_host_resolver,
)
from datadog_checks.base.utils.serialization import json
from datadog_checks.mysql import aws
from datadog_checks.mysql.cursor import CommenterCursor, CommenterDictCursor, CommenterSSCursor
from datadog_checks.mysql.health import MySqlHealth

from .__about__ import __version__
from .activity import MySQLActivity
from .collection_utils import collect_all_scalars, collect_scalar, collect_string, collect_type
from .config import MySQLConfig, sanitize
from .const import (
    AWS_RDS_HOSTNAME_SUFFIX,
    AZURE_DEPLOYMENT_TYPE_TO_RESOURCE_TYPE,
    BINLOG_VARS,
    COUNT,
    GALERA_VARS,
    GAUGE,
    GROUP_REPLICATION_VARS,
    GROUP_REPLICATION_VARS_8_0_2,
    INNODB_VARS,
    MONOTONIC,
    OPTIONAL_STATUS_VARS,
    OPTIONAL_STATUS_VARS_5_6_6,
    PERFORMANCE_VARS,
    PROC_NAME,
    RATE,
    REPLICA_VARS,
    SCHEMA_VARS,
    STATUS_VARS,
    SYNTHETIC_VARS,
    TABLE_ROWS_STATS_VARS,
    TABLE_VARS,
    VARIABLES_VARS,
)
from .global_variables import GlobalVariables
from .index_metrics import MySqlIndexMetrics
from .innodb_metrics import InnoDBMetrics
from .metadata import MySQLMetadata
from .queries import (
    QUERY_DEADLOCKS,
    QUERY_ERRORS_RAISED,
    QUERY_USER_CONNECTIONS,
    SQL_95TH_PERCENTILE,
    SQL_AVG_QUERY_RUN_TIME,
    SQL_GROUP_REPLICATION_MEMBER,
    SQL_GROUP_REPLICATION_MEMBER_8_0_2,
    SQL_GROUP_REPLICATION_METRICS,
    SQL_GROUP_REPLICATION_METRICS_8_0_2,
    SQL_GROUP_REPLICATION_PLUGIN_STATUS,
    SQL_INNODB_ENGINES,
    SQL_QUERY_SCHEMA_SIZE,
    SQL_QUERY_SYSTEM_TABLE_SIZE,
    SQL_QUERY_TABLE_ROWS_STATS,
    SQL_QUERY_TABLE_SIZE,
    SQL_REPLICA_PROCESS_LIST,
    SQL_REPLICA_WORKER_THREADS,
    SQL_REPLICATION_ROLE_AWS_AURORA,
    show_replica_status_query,
)
from .statement_samples import MySQLStatementSamples
from .statements import MySQLStatementMetrics
from .util import DatabaseConfigurationError, connect_with_session_variables
from .version_utils import parse_version

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import datadog_agent # type: ignore
except ImportError:
    from datadog_checks.base.stubs import datadog_agent


class MySql(DatabaseCheck):
    SERVICE_CHECK_NAME = 'mysql.can_connect'
    SLAVE_SERVICE_CHECK_NAME = 'mysql.replication.slave_running'
    REPLICA_SERVICE_CHECK_NAME = 'mysql.replication.replica_running'
    GROUP_REPLICATION_SERVICE_CHECK_NAME = 'mysql.replication.group.status'
    DEFAULT_MAX_CUSTOM_QUERIES = 20
    HA_SUPPORTED = True

    def __init__(self, name, init_config, instances):
        super(MySql, self).__init__(name, init_config, instances)
        self.health = MySqlHealth(self)
        self.qcache_stats = {}
        self.version = None
        self.is_mariadb = None
        self.server_uuid = None
        self.cluster_uuid = None
        self._resolved_hostname = None
        self._database_identifier = None
        self._agent_hostname = None
        self._database_hostname = None
        self._events_wait_current_enabled = None
        self._group_replication_active = None
        self._replication_role = None
        self._initialized_at = int(time.time() * 1000)
        self._config = MySQLConfig(self.instance, init_config)
        self.tag_manager = TagManager()
        self.tag_manager.set_tags_from_list(self._config.tags, replace=True)  # Initialize from static config tags
        self.add_core_tags()
        self._cloud_metadata = self._config.cloud_metadata

        # Create a new connection on every check run
        self._conn = None

        # Global variables manager
        self.global_variables = GlobalVariables()

        self._query_manager = QueryManager(self, self.execute_query_raw, queries=[])
        self.check_initializations.append(self._query_manager.compile_queries)
        self.innodb_stats = InnoDBMetrics()
        self.check_initializations.append(self._config.configuration_checks)
        self._warnings_by_code = {}

        # Determine if using AWS managed authentication
        self._uses_aws_managed_auth = (
            'aws' in self.cloud_metadata
            and 'managed_authentication' in self.cloud_metadata.get('aws', {})
            and self.cloud_metadata['aws']['managed_authentication'].get('enabled', False)
        )

        # Pass function reference and managed auth flag to async jobs
        self._statement_metrics = MySQLStatementMetrics(
            self, self._config, self._get_connection_args, self._uses_aws_managed_auth
        )
        self._statement_samples = MySQLStatementSamples(
            self, self._config, self._get_connection_args, self._uses_aws_managed_auth
        )
        self._mysql_metadata = MySQLMetadata(self, self._config, self._get_connection_args, self._uses_aws_managed_auth)
        self._query_activity = MySQLActivity(self, self._config, self._get_connection_args, self._uses_aws_managed_auth)
        self._index_metrics = MySqlIndexMetrics(self._config)
        # _database_instance_emitted: limit the collection and transmission of the database instance metadata
        self._database_instance_emitted = TTLCache(
            maxsize=1,
            ttl=self._config.database_instance_collection_interval,
        )  # type: TTLCache

        self._runtime_queries_cached = None
        self.set_resource_tags()
        self._is_innodb_engine_enabled_cached = None

        self._submit_initialization_health_event()

    def _submit_initialization_health_event(self):
        try:
            # Handle the config validation result after we've set tags so those tags are included in the health event
            # TODO: validate the config once it is refactored similar to Postgres, and then send the computed config
            self.health.submit_health_event(
                name=HealthEvent.INITIALIZATION,
                status=HealthStatus.OK,
                cooldown_time=60 * 60 * 6,  # 6 hours
                data={"initialized_at": self._initialized_at, "instance": sanitize(self.instance)},
            )
        except Exception as e:
            self.log.error("Error submitting health event for initialization: %s", e)

    def execute_query_raw(self, query):
        with closing(self._conn.cursor(CommenterSSCursor)) as cursor:
            cursor.execute(query)
            for row in cursor.fetchall_unbuffered():
                yield row

    @AgentCheck.metadata_entrypoint
    def _send_metadata(self):
        self.set_metadata('version', self.version.version + '+' + self.version.build)
        self.set_metadata('flavor', self.version.flavor)
        self.set_metadata('resolved_hostname', self.resolved_hostname)

    @property
    def tags(self):
        return self.tag_manager.get_tags()

    @property
    def reported_hostname(self):
        # type: () -> str
        if self._config.exclude_hostname:
            return None
        return self.resolved_hostname

    @property
    def resolved_hostname(self):
        # type: () -> str
        if self._resolved_hostname is None:
            if self._config.reported_hostname:
                self._resolved_hostname = self._config.reported_hostname
            else:
                self._resolved_hostname = self.resolve_db_host()
        return self._resolved_hostname

    @property
    def tags(self):
        return self.tag_manager.get_tags()

    @property
    def cloud_metadata(self):
        return self._cloud_metadata

    @property
    def dbms_version(self):
        if self.version is None:
            return None
        return self.version.version + '+' + self.version.build

    @property
    def database_identifier(self):
        # type: () -> str
        if self._database_identifier is None:
            template = Template(self._config.database_identifier.get('template') or '$resolved_hostname')
            tag_dict = {}
            tags = self.tag_manager.get_tags()
            # sort tags to ensure consistent ordering
            tags.sort()
            for t in tags:
                if ':' in t:
                    key, value = t.split(':', 1)
                    if key in tag_dict:
                        tag_dict[key] += f",{value}"
                    else:
                        tag_dict[key] = value
            tag_dict['resolved_hostname'] = self.resolved_hostname
            tag_dict['host'] = str(self._config.host)
            tag_dict['port'] = str(self._config.port)
            tag_dict['mysql_sock'] = str(self._config.mysql_sock)
            self._database_identifier = template.safe_substitute(**tag_dict)
        return self._database_identifier

    @property
    def agent_hostname(self):
        # type: () -> str
        if self._agent_hostname is None:
            self._agent_hostname = datadog_agent.get_hostname()
        return self._agent_hostname

    @property
    def database_hostname(self):
        # type: () -> str
        if self._database_hostname is None:
            self._database_hostname = self.resolve_db_host()
        return self._database_hostname

    @property
    def events_wait_current_enabled(self):
        # type: () -> bool
        if self._events_wait_current_enabled is None:
            self._check_events_wait_current_enabled(self._conn)
        return self._events_wait_current_enabled

    def add_core_tags(self):
        """
        Add tags that should be attached to every metric/event but which require check calculations outside the config.
        """
        self.tag_manager.set_tag("database_hostname", self.database_hostname, replace=True)
        self.tag_manager.set_tag("database_instance", self.database_identifier, replace=True)

    def set_resource_tags(self):
        if self.cloud_metadata.get("gcp") is not None:
            self.tag_manager.set_tag(
                "dd.internal.resource",
                "gcp_sql_database_instance:{}:{}".format(
                    self.cloud_metadata.get("gcp")["project_id"], self.cloud_metadata.get("gcp")["instance_id"]
                ),
            )
        if self.cloud_metadata.get("aws") is not None:
            self.tag_manager.set_tag(
                "dd.internal.resource",
                "aws_rds_instance:{}".format(
                    self.cloud_metadata.get("aws")["instance_endpoint"],
                ),
            )
        elif AWS_RDS_HOSTNAME_SUFFIX in self.resolved_hostname:
            # allow for detecting if the host is an RDS host, and emit
            # the resource properly even if the `aws` config is unset
            self.tag_manager.set_tag(
                "dd.internal.resource",
                "aws_rds_instance:{}".format(self.resolved_hostname),
            )
            self.cloud_metadata["aws"] = {
                "instance_endpoint": self.resolved_hostname,
            }
        if self.cloud_metadata.get("azure") is not None:
            deployment_type = self.cloud_metadata.get("azure")["deployment_type"]
            # some `deployment_type`s map to multiple `resource_type`s
            resource_type = AZURE_DEPLOYMENT_TYPE_TO_RESOURCE_TYPE.get(deployment_type)
            if resource_type:
                self.tag_manager.set_tag(
                    "dd.internal.resource",
                    "{}:{}".format(resource_type, self.cloud_metadata.get("azure")["name"]),
                )
        # finally, emit a `database_instance` resource for this instance
        self.tag_manager.set_tag(
            "dd.internal.resource",
            "database_instance:{}".format(
                self.database_identifier,
            ),
        )

    def set_version(self):
        self.version = parse_version(self.global_variables.version, self.global_variables.version_comment)
        self.is_mariadb = self.version.flavor == "MariaDB"
        self.tag_manager.set_tag("dbms_flavor", self.version.flavor.lower(), replace=True)

    def set_server_uuid(self):
        # MariaDB does not support server_uuid
        if self.is_mariadb:
            return
        self.server_uuid = self.global_variables.server_uuid
        if self.server_uuid:
            self.tag_manager.set_tag("server_uuid", self.server_uuid, replace=True)

    def _check_database_configuration(self, db):
        self._check_events_wait_current_enabled(db)
        self._is_group_replication_active(db)

    def _check_events_wait_current_enabled(self, db):
        if not self._config.dbm_enabled or not self._config.activity_config.get("enabled", True):
            self.log.debug("skipping _check_events_wait_current_enabled because dbm activity collection is not enabled")
            return
        if not self.global_variables.performance_schema_enabled:
            # set events_wait_current_enabled to False if performance_schema is not enabled
            self.log.debug('`performance_schema` is required to enable `events_waits_current`')
            self._events_wait_current_enabled = False
            return self._events_wait_current_enabled
        with closing(db.cursor(CommenterCursor)) as cursor:
            cursor.execute(
                """\
                SELECT
                    NAME,
                    ENABLED
                FROM performance_schema.setup_consumers WHERE NAME = 'events_waits_current'
                """
            )
            results = dict(cursor.fetchall())
            events_wait_current_enabled = self._get_variable_enabled(results, 'events_waits_current')
            self.log.debug(
                '`events_wait_current_enabled` was %s. Setting it to %s',
                self._events_wait_current_enabled,
                events_wait_current_enabled,
            )
            self._events_wait_current_enabled = events_wait_current_enabled
        return self._events_wait_current_enabled

    def resolve_db_host(self):
        return agent_host_resolver(self._config.host)

    def _get_debug_tags(self):
        return ['agent_hostname:{}'.format(datadog_agent.get_hostname())]

    def debug_stats_kwargs(self, tags=None):
        tags = self.tag_manager.get_tags() + self._get_debug_tags() + (tags or [])
        return {
            'tags': tags,
            "hostname": self.resolved_hostname,
        }

    @classmethod
    def get_library_versions(cls):
        return {'pymysql': pymysql.__version__}

    def check(self, _):
        self._submit_initialization_health_event()

        if self.instance.get('user'):
            self._log_deprecation('_config_renamed', 'user', 'username')

        if self.instance.get('pass'):
            self._log_deprecation('_config_renamed', 'pass', 'password')

        self._set_qcache_stats()
        try:
            with self._connect() as db:
                self._conn = db

                # Collect global variables early for use throughout the check
                self.global_variables.collect(db)

                # version collection
                self.set_version()
                self._send_metadata()
                self._check_database_configuration(db)

                self.set_server_uuid()
                self.set_cluster_tags(db)

                # Update tag set with relevant information
                if self.global_variables.is_aurora:
                    role = self._get_aurora_replication_role(db)
                    self._update_aurora_replication_role(role)

                # All data collection starts here
                self._send_database_instance_metadata()

                # Metric collection
                tags = self.tag_manager.get_tags()
                if not self._config.only_custom_queries:
                    self._collect_metrics(db, tags=tags)
                    self._collect_system_metrics(self._config.host, db, tags)
                    if self._get_runtime_queries(db):
                        self._get_runtime_queries(db).execute(extra_tags=tags)

                if self._config.dbm_enabled:
                    dbm_tags = list(set(self.service_check_tags) | set(tags))
                    self._statement_metrics.run_job_loop(dbm_tags)
                    self._statement_samples.run_job_loop(dbm_tags)
                    self._query_activity.run_job_loop(dbm_tags)
                    self._mysql_metadata.run_job_loop(dbm_tags)

                # keeping track of these:
                self._put_qcache_stats()

                # Custom queries
                self._query_manager.execute(extra_tags=tags)

        except Exception as e:
            self.log.exception("error!")
            raise e
        finally:
            self._conn = None
            self._report_warnings()

    def cancel(self):
        self._statement_samples.cancel()
        self._statement_metrics.cancel()
        self._query_activity.cancel()
        self._mysql_metadata.cancel()

    def _new_query_executor(self, queries):
        return QueryExecutor(
            self.execute_query_raw,
            self,
            queries=queries,
            hostname=self.reported_hostname,
            track_operation_time=True,
        )

    def _get_runtime_queries(self, db):
        """
        Initializes runtime queries which depend on outside factors (e.g. permission checks) to load first.
        """
        if self._runtime_queries_cached:
            return self._runtime_queries_cached

        queries = []

        if self._check_innodb_engine_enabled(db):
            queries.extend([QUERY_DEADLOCKS])

        if self.global_variables.performance_schema_enabled:
            queries.extend([QUERY_USER_CONNECTIONS])
            if not self.is_mariadb and self.version.version_compatible((8, 0, 0)) and self._config.dbm_enabled:
                error_query = QUERY_ERRORS_RAISED.copy()
                error_query['query'] = error_query['query'].format(user=self._config.user)
                queries.extend([error_query])
        if self._index_metrics.include_index_metrics:
            queries.extend(self._index_metrics.queries)
        self._runtime_queries_cached = self._new_query_executor(queries)
        self._runtime_queries_cached.compile_queries()
        self.log.debug("initialized runtime queries")
        return self._runtime_queries_cached

    def _set_qcache_stats(self):
        host_key = self._get_host_key()
        qcache_st = self.qcache_stats.get(host_key, (None, None, None))

        self._qcache_hits = qcache_st[0]
        self._qcache_inserts = qcache_st[1]
        self._qcache_not_cached = qcache_st[2]

    def _put_qcache_stats(self):
        host_key = self._get_host_key()
        self.qcache_stats[host_key] = (self._qcache_hits, self._qcache_inserts, self._qcache_not_cached)

    def _get_host_key(self):
        if self._config.defaults_file:
            return self._config.defaults_file

        hostkey = self._config.host
        if self._config.mysql_sock:
            hostkey = "{0}:{1}".format(hostkey, self._config.mysql_sock)
        elif self._config.port:
            hostkey = "{0}:{1}".format(hostkey, self._config.port)

        return hostkey

    def _get_connection_args(self):
        ssl = dict(self._config.ssl) if self._config.ssl else None
        connection_args = {
            'ssl': ssl,
            'connect_timeout': self._config.connect_timeout,
            'read_timeout': self._config.read_timeout,
            'autocommit': True,
        }
        if self._config.charset:
            connection_args['charset'] = self._config.charset

        if self._config.defaults_file != '':
            connection_args['read_default_file'] = self._config.defaults_file
            return connection_args

        connection_args.update({'user': self._config.user, 'passwd': self._config.password})
        if self._uses_aws_managed_auth:
            # Generate AWS IAM auth token
            aws_managed_authentication = self.cloud_metadata['aws']['managed_authentication']
            region = self.cloud_metadata['aws']['region']
            password = aws.generate_rds_iam_token(
                host=self._config.host,
                username=self._config.user,
                port=self._config.port,
                region=region,
                role_arn=aws_managed_authentication.get('role_arn'),
            )
            connection_args.update({'user': self._config.user, 'passwd': password})
        if self._config.mysql_sock != '':
            self.service_check_tags = self._service_check_tags(self._config.mysql_sock)
            connection_args.update({'unix_socket': self._config.mysql_sock})
        else:
            connection_args.update({'host': self._config.host})

        if self._config.port:
            connection_args.update({'port': self._config.port})
        return connection_args

    def _service_check_tags(self, server=None):
        # type: (Optional[str]) -> List[str]
        if server is None:
            server = self._config.mysql_sock if self._config.mysql_sock != '' else self._config.host
        service_check_tags = [
            'port:{}'.format(self._config.port if self._config.port else 'unix_socket'),
        ] + self.tag_manager.get_tags()
        if not self.disable_generic_tags:
            service_check_tags.append('server:{0}'.format(server))
        return service_check_tags

    @contextmanager
    def _connect(self):
        service_check_tags = self._service_check_tags()
        db = None
        try:
            connect_args = self._get_connection_args()
            db = connect_with_session_variables(**connect_args)
            self.log.debug("Connected to MySQL")
            self.service_check_tags = list(set(service_check_tags))
            self.service_check(
                self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=service_check_tags, hostname=self.reported_hostname
            )
            yield db
        except Exception:
            self.service_check(
                self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=service_check_tags, hostname=self.reported_hostname
            )
            raise
        finally:
            if db:
                db.close()

    def _collect_metrics(self, db, tags):
        # Get aggregate of all VARS we want to collect
        metrics = copy.deepcopy(STATUS_VARS)

        # collect results from db
        with tracked_query(self, operation="status_metrics"):
            results = self._get_stats_from_status(db)
        with tracked_query(self, operation="variables_metrics"):
            # Use cached global variables instead of making a separate query
            results.update(self.global_variables.all_variables)

        if self._check_innodb_engine_enabled(db):
            # Innodb metrics are not available for Aurora reader instances
            if self.global_variables.is_aurora and self._replication_role == "reader":
                self.log.debug("Skipping innodb metrics collection for reader instance")
            else:
                with tracked_query(self, operation="innodb_metrics"):
                    results.update(self.innodb_stats.get_stats_from_innodb_status(db))
            self.innodb_stats.process_innodb_stats(results, self._config.options, metrics)

        # Binary log statistics
        if self.global_variables.log_bin_enabled:
            with tracked_query(self, operation="binary_log_metrics"):
                results['Binlog_space_usage_bytes'] = self._get_binary_log_stats(db)

        # Compute key cache utilization metric
        key_blocks_unused = collect_scalar('Key_blocks_unused', results)
        key_cache_block_size = self.global_variables.key_cache_block_size
        key_buffer_size = self.global_variables.key_buffer_size
        results['Key_buffer_size'] = key_buffer_size

        try:
            # can be null if the unit is missing in the user config (4 instead of 4G for eg.)
            if key_buffer_size != 0:
                key_cache_utilization = 1 - ((key_blocks_unused * key_cache_block_size) / key_buffer_size)
                results['Key_cache_utilization'] = key_cache_utilization

            results['Key_buffer_bytes_used'] = collect_scalar('Key_blocks_used', results) * key_cache_block_size
            results['Key_buffer_bytes_unflushed'] = (
                collect_scalar('Key_blocks_not_flushed', results) * key_cache_block_size
            )
        except TypeError as e:
            self.log.error("Not all Key metrics are available, unable to compute: %s", e)

        metrics.update(VARIABLES_VARS)
        metrics.update(INNODB_VARS)
        metrics.update(BINLOG_VARS)

        if is_affirmative(self._config.options.get('extra_status_metrics', self._config.dbm_enabled)):
            self.log.debug("Collecting Extra Status Metrics")
            metrics.update(OPTIONAL_STATUS_VARS)

            if self.version.version_compatible((5, 6, 6)):
                metrics.update(OPTIONAL_STATUS_VARS_5_6_6)

        if is_affirmative(self._config.options.get('galera_cluster', False)):
            # already in result-set after 'SHOW STATUS' just add vars to collect
            self.log.debug("Collecting Galera Metrics.")
            metrics.update(GALERA_VARS)

        above_560 = self.version.version_compatible((5, 6, 0))
        if (
            is_affirmative(self._config.options.get('extra_performance_metrics', False))
            and above_560
            and self.global_variables.performance_schema_enabled
        ):
            self.warning(
                "[Deprecated] The `extra_performance_metrics` option will be removed in a future release. "
                "Utilize the `custom_queries` feature if the functionality is needed.",
            )
            with tracked_query(self, operation="exec_time_95th_metrics"):
                results['perf_digest_95th_percentile_avg_us'] = self._get_query_exec_time_95th_us(db)
            with tracked_query(self, operation="exec_time_per_schema_metrics"):
                results['query_run_time_avg'] = self._query_exec_time_per_schema(db)
            metrics.update(PERFORMANCE_VARS)

        if is_affirmative(self._config.options.get('schema_size_metrics', False)):
            # report avg query response time per schema to Datadog
            with tracked_query(self, operation="schema_size_metrics"):
                results['information_schema_size'] = self._query_size_per_schema(db)
            metrics.update(SCHEMA_VARS)

        if self._config.table_rows_stats_enabled and self.global_variables.userstat_enabled:
            # report size of tables in MiB to Datadog
            self.log.debug("Collecting Table Row Stats Metrics.")
            with tracked_query(self, operation="table_rows_stats_metrics"):
                (rows_read_total, rows_changed_total) = self._query_rows_stats_per_table(db)
            results['information_table_rows_read_total'] = rows_read_total
            results['information_table_rows_changed_total'] = rows_changed_total
            metrics.update(TABLE_ROWS_STATS_VARS)

        if is_affirmative(self._config.options.get('table_size_metrics', False)):
            # report size of tables in MiB to Datadog
            with tracked_query(self, operation="table_size_metrics"):
                (table_index_size, table_data_size) = self._query_size_per_table(db)
            results['information_table_index_size'] = table_index_size
            results['information_table_data_size'] = table_data_size
            metrics.update(TABLE_VARS)

        if is_affirmative(self._config.options.get('system_table_size_metrics', False)):
            # report size of tables in MiB to Datadog
            with tracked_query(self, operation="system_table_size_metrics"):
                (table_index_size, table_data_size) = self._query_size_per_table(db, system_tables=True)
            if results.get('information_table_index_size'):
                results['information_table_index_size'].update(table_index_size)
            else:
                results['information_table_index_size'] = table_index_size
            if results.get('information_table_data_size'):
                results['information_table_data_size'].update(table_data_size)
            else:
                results['information_table_data_size'] = table_data_size
            metrics.update(TABLE_VARS)

        if self._config.replication_enabled:
            if self.global_variables.performance_schema_enabled and self._group_replication_active:
                self.log.debug('Collecting group replication metrics.')
                with tracked_query(self, operation="group_replication_metrics"):
                    self._collect_group_replica_metrics(db, results)
            else:
                with tracked_query(self, operation="replication_metrics"):
                    replication_metrics = self._collect_replication_metrics(db, results, above_560)
                metrics.update(replication_metrics)
                self._check_replication_status(results)

        if len(self._config.additional_status) > 0:
            additional_status_dict = {}
            for status_dict in self._config.additional_status:
                status_name = status_dict["name"]
                status_metric = status_dict["metric_name"]
                if status_name in metrics.keys():
                    collected_metric = metrics.get(status_name)[0]
                    self.log.debug(
                        "Skipping status variable %s for metric %s as it is already collected by %s",
                        status_name,
                        status_metric,
                        collected_metric,
                    )
                else:
                    additional_status_dict[status_name] = (status_metric, status_dict["type"])
            metrics.update(additional_status_dict)

        if len(self._config.additional_variable) > 0:
            additional_variable_dict = {}
            for variable_dict in self._config.additional_variable:
                variable_name = variable_dict["name"]
                variable_metric = variable_dict["metric_name"]
                if variable_name in metrics.keys():
                    collected_metric = metrics.get(variable_name)[0]
                    self.log.debug(
                        "Skipping variable %s for metric %s as it is already collected by %s",
                        variable_name,
                        variable_metric,
                        collected_metric,
                    )
                else:
                    additional_variable_dict[variable_name] = (variable_metric, variable_dict["type"])

            metrics.update(additional_variable_dict)

        # "synthetic" metrics
        metrics.update(SYNTHETIC_VARS)
        self._compute_synthetic_results(results)

        # remove uncomputed metrics
        for k in SYNTHETIC_VARS:
            if k not in results:
                metrics.pop(k, None)

        # add duped metrics - reporting some as both rate and gauge
        dupes = [
            ('Table_locks_waited', 'Table_locks_waited_rate'),
            ('Table_locks_immediate', 'Table_locks_immediate_rate'),
        ]
        for src, dst in dupes:
            if src in results:
                results[dst] = results[src]

        self._submit_metrics(metrics, results, tags)

        # Collect custom query metrics
        # Max of 20 queries allowed
        if isinstance(self._config.queries, list):
            for check in self._config.queries[: self._config.max_custom_queries]:
                total_tags = tags + check.get('tags', [])
                self._collect_dict(
                    check['type'], {check['field']: check['metric']}, check['query'], db, tags=total_tags
                )

            if len(self._config.queries) > self._config.max_custom_queries:
                self.warning(
                    "Maximum number (%s) of custom queries reached. Skipping the rest.", self._config.max_custom_queries
                )

    def _collect_replication_metrics(self, db, results, above_560):
        # Get replica stats
        results.update(self._get_replica_stats(db))
        results.update(self._get_replicas_connected_count(db, above_560))
        return REPLICA_VARS

    def _collect_group_replica_metrics(self, db, results):
        try:
            with closing(db.cursor(CommenterCursor)) as cursor:
                # Version 8.0.2 introduced new columns to replication_group_members and replication_group_member_stats
                above_802 = self.version.version_compatible((8, 0, 2))
                query_to_execute = SQL_GROUP_REPLICATION_MEMBER_8_0_2 if above_802 else SQL_GROUP_REPLICATION_MEMBER
                cursor.execute(query_to_execute)
                replica_results = cursor.fetchone()
                status = self.OK
                additional_tags = []
                if replica_results is None or len(replica_results) < 2:
                    self.log.warning(
                        'Unable to get group replica status, setting mysql.replication.group.status as CRITICAL'
                    )
                    status = self.CRITICAL
                else:
                    status = self.OK if replica_results[1] == 'ONLINE' else self.CRITICAL
                    additional_tags = [
                        'channel_name:{}'.format(replica_results[0]),
                        'member_state:{}'.format(replica_results[1]),
                    ]
                    if above_802 and len(replica_results) > 2:
                        additional_tags.append('member_role:{}'.format(replica_results[2]))
                    self.gauge(
                        'mysql.replication.group.member_status', 1, tags=additional_tags + self.tag_manager.get_tags()
                    )

                self.service_check(
                    self.GROUP_REPLICATION_SERVICE_CHECK_NAME,
                    status=status,
                    tags=self.service_check_tags + additional_tags,
                )

                metrics_to_fetch = SQL_GROUP_REPLICATION_METRICS_8_0_2 if above_802 else SQL_GROUP_REPLICATION_METRICS

                cursor.execute(metrics_to_fetch)
                r = cursor.fetchone()

                if r is None:
                    self.log.warning('Unable to get group replication metrics')
                    return {}

                results = {
                    'Transactions_count': r[1],
                    'Transactions_check': r[2],
                    'Conflict_detected': r[3],
                    'Transactions_row_validating': r[4],
                }
                vars_to_submit = copy.deepcopy(GROUP_REPLICATION_VARS)
                if above_802:
                    results['Transactions_remote_applier_queue'] = r[5]
                    results['Transactions_remote_applied'] = r[6]
                    results['Transactions_local_proposed'] = r[7]
                    results['Transactions_local_rollback'] = r[8]
                    vars_to_submit.update(GROUP_REPLICATION_VARS_8_0_2)

                # Submit metrics now, so it's possible to attach `channel_name` tag
                self._submit_metrics(
                    vars_to_submit, results, self.tag_manager.get_tags() + ['channel_name:{}'.format(r[0])]
                )

                return vars_to_submit
        except Exception as e:
            self.warning("Internal error happened during the group replication check: %s", e)
            return {}

    def _check_replication_status(self, results):
        # Replica_IO_Running: Whether the I/O thread for reading the source's binary log is running.
        # You want this to be Yes unless you have not yet started replication or have explicitly stopped it.
        replica_io_running = collect_type('Slave_IO_Running', results, dict)
        if replica_io_running is None:
            replica_io_running = collect_type('Replica_IO_Running', results, dict)
        # Replica_SQL_Running: Whether the SQL thread for executing events in the relay log is running.
        replica_sql_running = collect_type('Slave_SQL_Running', results, dict)
        if replica_sql_running is None:
            replica_sql_running = collect_type('Replica_SQL_Running', results, dict)
        if replica_io_running:
            replica_io_running = any(v.lower().strip() == 'yes' for v in replica_io_running.values())
        if replica_sql_running:
            replica_sql_running = any(v.lower().strip() == 'yes' for v in replica_sql_running.values())

        # replicas will only be collected if user has PROCESS privileges.
        replicas = collect_scalar('Slaves_connected', results)
        if replicas is None:
            replicas = collect_scalar('Replicas_connected', results)

        # If the host act as a source
        source_repl_running_status = AgentCheck.UNKNOWN
        if self._is_source_host(replicas, results):
            if replicas > 0 and self.global_variables.log_bin_enabled:
                self.log.debug("Host is master, there are replicas and binlog is running")
                source_repl_running_status = AgentCheck.OK
            else:
                source_repl_running_status = AgentCheck.WARNING

            self._submit_replication_status(source_repl_running_status, ['replication_mode:source'])

        # If the host act as a replica
        # A host can be both a source and a replica
        # See https://dev.mysql.com/doc/refman/8.0/en/replication-solutions-performance.html
        # get replica running form global status page
        replica_running_status = AgentCheck.UNKNOWN
        if self._is_replica_host(replicas, results):
            if not (replica_io_running is None and replica_sql_running is None):
                if not replica_io_running and not replica_sql_running:
                    self.log.debug("Replica_IO_Running and Replica_SQL_Running are not ok")
                    replica_running_status = AgentCheck.CRITICAL
                elif not replica_io_running or not replica_sql_running:
                    self.log.debug("Either Replica_IO_Running or Replica_SQL_Running are not ok")
                    replica_running_status = AgentCheck.WARNING
                else:
                    self.log.debug("Replica_IO_Running and Replica_SQL_Running are ok")
                    replica_running_status = AgentCheck.OK

                self._submit_replication_status(replica_running_status, ['replication_mode:replica'])

    def _submit_replication_status(self, status, additional_tags):
        # deprecated in favor of service_check("mysql.replication.slave_running")
        self.gauge(
            name=self.SLAVE_SERVICE_CHECK_NAME,
            value=1 if status == AgentCheck.OK else 0,
            tags=self.tag_manager.get_tags() + additional_tags,
            hostname=self.reported_hostname,
        )
        # deprecated in favor of service_check("mysql.replication.replica_running")
        self.service_check(
            self.SLAVE_SERVICE_CHECK_NAME,
            status,
            tags=self.service_check_tags + additional_tags,
            hostname=self.reported_hostname,
        )
        self.service_check(
            self.REPLICA_SERVICE_CHECK_NAME,
            status,
            tags=self.service_check_tags + additional_tags,
            hostname=self.reported_hostname,
        )

    def _is_source_host(self, replicas, results):
        # type: (float, Dict[str, Any]) -> bool
        # master uuid only collected in replicas
        source_host = collect_string('Master_Host', results) or collect_string('Source_Host', results)
        if replicas > 0 or not source_host:
            return True

        return False

    def _is_replica_host(self, replicas, results):
        return collect_string('Master_Host', results) or collect_string('Source_Host', results)

    def _is_group_replication_active(self, db):
        if not self._config.replication_enabled:
            self.log.debug("Replication is not enabled, skipping group replication check")
            self._group_replication_active = False
            return self._group_replication_active

        with closing(db.cursor(CommenterCursor)) as cursor:
            cursor.execute(SQL_GROUP_REPLICATION_PLUGIN_STATUS)
            r = cursor.fetchone()

            # Plugin is installed
            if r is not None and r[0].lower() == 'active':
                self.log.debug('Group replication plugin is detected and active')
                self._group_replication_active = True
                return self._group_replication_active
            else:
                self.log.debug('Group replication plugin not detected')
                self._group_replication_active = False
                return self._group_replication_active

    def _submit_metrics(self, variables, db_results, tags):
        for variable, metric in variables.items():
            if isinstance(metric, list):
                for m in metric:
                    metric_name, metric_type = m
                    self.__submit_metric(metric_name, metric_type, variable, db_results, tags)
            else:
                metric_name, metric_type = metric
                self.__submit_metric(metric_name, metric_type, variable, db_results, tags)

    def __submit_metric(self, metric_name, metric_type, variable, db_results, tags):
        for tag, value in collect_all_scalars(variable, db_results):
            metric_tags = list(tags)
            if tag:
                if "," in tag:
                    t_split = tag.split(",")
                    for t in t_split:
                        metric_tags.append(t)
                else:
                    metric_tags.append(tag)
            if value is not None:
                if metric_type == RATE:
                    self.rate(metric_name, value, tags=metric_tags, hostname=self.reported_hostname)
                elif metric_type == GAUGE:
                    self.gauge(metric_name, value, tags=metric_tags, hostname=self.reported_hostname)
                elif metric_type == COUNT:
                    self.count(metric_name, value, tags=metric_tags, hostname=self.reported_hostname)
                elif metric_type == MONOTONIC:
                    self.monotonic_count(metric_name, value, tags=metric_tags, hostname=self.reported_hostname)

    def _collect_dict(self, metric_type, field_metric_map, query, db, tags):
        """
        Query status and get a dictionary back.
        Extract each field out of the dictionary
        and stuff it in the corresponding metric.

        query: show status...
        field_metric_map: {"Seconds_behind_master": "mysqlSecondsBehindMaster"}
        """
        try:
            with closing(db.cursor(CommenterCursor)) as cursor:
                cursor.execute(query)
                result = cursor.fetchone()
                if result is not None:
                    for field, metric in field_metric_map.items():
                        # Find the column name in the cursor description to identify the column index
                        # http://www.python.org/dev/peps/pep-0249/
                        # cursor.description is a tuple of (column_name, ..., ...)
                        try:
                            col_idx = [d[0].lower() for d in cursor.description].index(field.lower())
                            self.log.debug("Collecting metric: %s", metric)
                            if result[col_idx] is not None:
                                self.log.debug("Collecting done, value %s", result[col_idx])
                                if metric_type == GAUGE:
                                    self.gauge(
                                        metric, float(result[col_idx]), tags=tags, hostname=self.reported_hostname
                                    )
                                elif metric_type == RATE:
                                    self.rate(
                                        metric, float(result[col_idx]), tags=tags, hostname=self.reported_hostname
                                    )
                                else:
                                    self.gauge(
                                        metric, float(result[col_idx]), tags=tags, hostname=self.reported_hostname
                                    )
                            else:
                                self.log.debug("Received value is None for index %d", col_idx)
                        except ValueError:
                            self.log.exception("Cannot find %s in the columns %s", field, cursor.description)
        except Exception:
            self.warning("Error while running %s\n%s", query, traceback.format_exc())
            self.log.exception("Error while running %s", query)

    def _get_aurora_replication_role(self, db):
        role = None
        try:
            with closing(db.cursor(CommenterCursor)) as cursor:
                cursor.execute(SQL_REPLICATION_ROLE_AWS_AURORA)
                replication_role = cursor.fetchone()[0]
                if replication_role in {'writer', 'reader'}:
                    role = replication_role
        except Exception:
            self.log.warning("Error occurred while fetching Aurora runtime tags: %s", traceback.format_exc())
        return role

    def _update_aurora_replication_role(self, replication_role):
        """
        Updates the replication_role tag with the aurora replication role if it exists
        """
        if replication_role:
            self.tag_manager.set_tag('replication_role', replication_role, replace=True)
            self._replication_role = replication_role

    def _collect_system_metrics(self, host, db, tags):
        pid = None
        # The server needs to run locally, accessed by TCP or socket
        if host in ["localhost", "127.0.0.1", "0.0.0.0"] or db.port == int(0):
            pid = self._get_server_pid(db)

        if pid:
            self.log.debug("System metrics for mysql w/ pid: %s", pid)
            # At last, get mysql cpu data out of psutil or procfs

            try:
                if PSUTIL_AVAILABLE:
                    self.log.debug("psutil is available, attempting to collect mysql.performance.* metrics")
                    proc = psutil.Process(pid)

                    ucpu = proc.cpu_times()[0]
                    scpu = proc.cpu_times()[1]

                    if ucpu and scpu:
                        self.rate("mysql.performance.user_time", ucpu, tags=tags, hostname=self.reported_hostname)
                        # should really be system_time
                        self.rate("mysql.performance.kernel_time", scpu, tags=tags, hostname=self.reported_hostname)
                        self.rate("mysql.performance.cpu_time", ucpu + scpu, tags=tags, hostname=self.reported_hostname)
                else:
                    self.log.debug("psutil is not available, will not collect mysql.performance.* metrics")
            except Exception:
                self.warning("Error while reading mysql (pid: %s) procfs data\n%s", pid, traceback.format_exc())

    def _get_server_pid(self, db):
        pid = None

        # Try to get pid from pid file, it can fail for permission reason
        pid_file = self.global_variables.pid_file
        if pid_file is not None:
            self.log.debug("pid file: %s", str(pid_file))
            try:
                with open(pid_file, 'rb') as f:
                    pid = int(f.readline())
            except IOError:
                self.log.debug("Cannot read mysql pid file %s", pid_file)

        process_name = [PROC_NAME]
        if self.is_mariadb and self.version.version_compatible((10, 5, 0)):
            process_name.append("mariadbd")

        # If pid has not been found, read it from ps
        if pid is None and PSUTIL_AVAILABLE:
            for proc in psutil.process_iter():
                try:
                    if proc.name() in process_name:
                        pid = proc.pid
                except (psutil.AccessDenied, psutil.ZombieProcess, psutil.NoSuchProcess):
                    continue
                except Exception:
                    self.log.exception("Error while fetching mysql pid from psutil")

        return pid

    @classmethod
    def _get_stats_from_status(cls, db):
        with closing(db.cursor(CommenterCursor)) as cursor:
            cursor.execute("SHOW /*!50002 GLOBAL */ STATUS;")
            results = dict(cursor.fetchall())

            return results

    def _get_binary_log_stats(self, db):
        try:
            with closing(db.cursor(CommenterCursor)) as cursor:
                cursor.execute("SHOW BINARY LOGS;")
                cursor_results = cursor.fetchall()
                master_logs = {result[0]: result[1] for result in cursor_results}

                binary_log_space = 0
                for value in master_logs.values():
                    binary_log_space += value

                return binary_log_space
        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            self.warning("Privileges error accessing the BINARY LOGS (must grant REPLICATION CLIENT): %s", e)
            return None

    def _check_innodb_engine_enabled(self, db):
        # Whether InnoDB engine is available or not can be found out either
        # from the output of SHOW ENGINES or from information_schema.ENGINES
        # table. Later is chosen because that involves no string parsing.
        if self._is_innodb_engine_enabled_cached is not None:
            return self._is_innodb_engine_enabled_cached

        if self._config.disable_innodb_metrics:
            self.log.debug("disable_innodb_metrics config is set, disabling innodb metric collection")
            self._is_innodb_engine_enabled_cached = False
            return self._is_innodb_engine_enabled_cached

        try:
            with closing(db.cursor(CommenterCursor)) as cursor:
                cursor.execute(SQL_INNODB_ENGINES)
                self._is_innodb_engine_enabled_cached = cursor.rowcount > 0

        except (pymysql.err.InternalError, pymysql.err.OperationalError, pymysql.err.NotSupportedError) as e:
            self.warning("Possibly innodb stats unavailable - error querying engines table: %s", e)
            self._is_innodb_engine_enabled_cached = False
        return self._is_innodb_engine_enabled_cached

    def _get_replica_stats(self, db):
        replica_results = defaultdict(dict)
        replica_status = self._get_replica_replication_status(db)
        if replica_status:
            for replica in replica_status:
                # MySQL <5.7 does not have Channel_Name.
                # For MySQL >=5.7 'Channel_Name' is set to an empty string by default
                channel = self._config.replication_channel or replica.get('Channel_Name') or 'default'
                for key, value in replica.items():
                    if value is not None:
                        replica_results[key]['channel:{0}'.format(channel)] = value
        return replica_results

    def _get_replica_replication_status(self, db):
        results = []
        if not self._config.replication_enabled:
            return results

        try:
            with closing(db.cursor(CommenterDictCursor)) as cursor:
                if self.is_mariadb and self._config.replication_channel:
                    cursor.execute("SET @@default_master_connection = '{0}';".format(self._config.replication_channel))
                cursor.execute(
                    show_replica_status_query(self.version, self.is_mariadb, self._config.replication_channel)
                )

                results = cursor.fetchall()
                self.log.debug("Getting replication status: %s", results)
        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            errno, msg = e.args
            if errno == 1617 and msg == "There is no master connection '{0}'".format(self._config.replication_channel):
                # MariaDB complains when you try to get replica status with a
                # connection name on the master, without connection name it
                # responds an empty string as expected.
                # Mysql behaves the same with or without connection name.
                pass
            else:
                self.warning("Privileges error getting replication status (must grant REPLICATION CLIENT): %s", e)

        return results

    def _get_replicas_connected_count(self, db, above_560):
        """
        Retrieve the count of connected replicas using:
        1. The `performance_schema.threads` table. Non-blocking, requires version > 5.6.0
        2. The `information_schema.processlist` table. Blocking
        """
        try:
            with closing(db.cursor(CommenterCursor)) as cursor:
                if above_560 and self.global_variables.performance_schema_enabled:
                    # Query `performance_schema.threads` instead of `
                    # information_schema.processlist` to avoid mutex impact on performance.
                    cursor.execute(SQL_REPLICA_WORKER_THREADS)
                else:
                    cursor.execute(SQL_REPLICA_PROCESS_LIST)
                replica_results = cursor.fetchall()
                replicas = 0
                for _ in replica_results:
                    replicas += 1

                return {'Replicas_connected': replicas}

        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            self.warning("Privileges error accessing the process tables (must grant PROCESS): %s", e)
            return {}

    @classmethod
    def _are_values_numeric(cls, array):
        return all(v.isdigit() for v in array)

    @staticmethod
    def _get_variable_enabled(results, var):
        enabled = collect_string(var, results)
        return enabled and is_affirmative(enabled.lower().strip())

    def _get_query_exec_time_95th_us(self, db):
        # Fetches the 95th percentile query execution time and returns the value
        # in microseconds
        try:
            with closing(db.cursor(CommenterCursor)) as cursor:
                cursor.execute(SQL_95TH_PERCENTILE)

                if cursor.rowcount < 1:
                    self.warning(
                        "Failed to fetch records from the perf schema \
                                 'events_statements_summary_by_digest' table."
                    )
                    return None

                row = cursor.fetchone()
                query_exec_time_95th_per = row[0]

                return query_exec_time_95th_per
        except (pymysql.err.InternalError, pymysql.err.OperationalError, pymysql.err.InterfaceError) as e:
            self.warning("95th percentile performance metrics unavailable at this time: %s", e)
            return None

    def _query_exec_time_per_schema(self, db):
        # Fetches the avg query execution time per schema and returns the
        # value in microseconds
        try:
            with closing(db.cursor(CommenterCursor)) as cursor:
                cursor.execute(SQL_AVG_QUERY_RUN_TIME)

                if cursor.rowcount < 1:
                    self.warning(
                        "Failed to fetch records from the perf schema \
                                 'events_statements_summary_by_digest' table."
                    )
                    return None

                schema_query_avg_run_time = {}
                for row in cursor.fetchall():
                    schema_name = str(row[0])
                    avg_us = int(row[1])

                    # set the tag as the dictionary key
                    schema_query_avg_run_time["schema:{0}".format(schema_name)] = avg_us

                return schema_query_avg_run_time
        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            self.warning("Size of schemas metrics unavailable at this time: %s", e)

        return {}

    def _query_size_per_table(self, db, system_tables=False):
        try:
            with closing(db.cursor(CommenterCursor)) as cursor:
                if system_tables:
                    cursor.execute(SQL_QUERY_SYSTEM_TABLE_SIZE)
                else:
                    cursor.execute(SQL_QUERY_TABLE_SIZE)

                if cursor.rowcount < 1:
                    self.warning("Failed to fetch records from the information schema 'tables' table.")
                    return None, None

                table_index_size = {}
                table_data_size = {}
                for row in cursor.fetchall():
                    table_schema = str(row[0])
                    table_name = str(row[1])
                    index_size = float(row[2])
                    data_size = float(row[3])

                    # set the tag as the dictionary key
                    table_index_size["schema:{},table:{}".format(table_schema, table_name)] = index_size
                    table_data_size["schema:{},table:{}".format(table_schema, table_name)] = data_size

                return table_index_size, table_data_size
        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            self.warning("Size of tables metrics unavailable at this time: %s", e)

            return None, None

    def _query_size_per_schema(self, db):
        # Fetches the avg query execution time per schema and returns the
        # value in microseconds
        try:
            with closing(db.cursor(CommenterCursor)) as cursor:
                cursor.execute(SQL_QUERY_SCHEMA_SIZE)

                if cursor.rowcount < 1:
                    self.warning("Failed to fetch records from the information schema 'tables' table.")
                    return None

                schema_size = {}
                for row in cursor.fetchall():
                    schema_name = str(row[0])
                    size = int(row[1])

                    # set the tag as the dictionary key
                    schema_size["schema:{0}".format(schema_name)] = size

                return schema_size
        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            self.warning("Avg exec time performance metrics unavailable at this time: %s", e)

        return {}

    def _query_rows_stats_per_table(self, db):
        try:
            with closing(db.cursor(CommenterCursor)) as cursor:
                cursor.execute(SQL_QUERY_TABLE_ROWS_STATS)

                if cursor.rowcount < 1:
                    self.warning("Failed to fetch records from the tables rows stats 'tables' table.")
                    return None, None

                table_rows_read_total = {}
                table_rows_changed_total = {}
                for row in cursor.fetchall():
                    table_schema = str(row[0])
                    table_name = str(row[1])
                    rows_read_total = int(row[2])
                    rows_changed_total = int(row[3])

                    # set the tag as the dictionary key
                    table_rows_read_total["schema:{},table:{}".format(table_schema, table_name)] = rows_read_total
                    table_rows_changed_total["schema:{},table:{}".format(table_schema, table_name)] = rows_changed_total
                return table_rows_read_total, table_rows_changed_total
        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            self.warning("Tables rows stats metrics unavailable at this time: %s", e)

        return None, None

    def _compute_synthetic_results(self, results):
        if ('Qcache_hits' in results) and ('Qcache_inserts' in results) and ('Qcache_not_cached' in results):
            if not int(results['Qcache_hits']):
                results['Qcache_utilization'] = 0
            else:
                results['Qcache_utilization'] = (
                    float(results['Qcache_hits'])
                    / (int(results['Qcache_inserts']) + int(results['Qcache_not_cached']) + int(results['Qcache_hits']))
                    * 100
                )

            if all(v is not None for v in (self._qcache_hits, self._qcache_inserts, self._qcache_not_cached)):
                if not (int(results['Qcache_hits']) - self._qcache_hits):
                    results['Qcache_instant_utilization'] = 0
                else:
                    top = float(results['Qcache_hits']) - self._qcache_hits
                    bottom = (
                        (int(results['Qcache_inserts']) - self._qcache_inserts)
                        + (int(results['Qcache_not_cached']) - self._qcache_not_cached)
                        + (int(results['Qcache_hits']) - self._qcache_hits)
                    )
                    results['Qcache_instant_utilization'] = (top / bottom) * 100

            # update all three, or none - for consistent samples.
            self._qcache_hits = int(results['Qcache_hits'])
            self._qcache_inserts = int(results['Qcache_inserts'])
            self._qcache_not_cached = int(results['Qcache_not_cached'])

    def record_warning(self, code, message):
        # type: (DatabaseConfigurationError, str) -> None
        self._warnings_by_code[code] = message

    def _report_warnings(self):
        messages = self._warnings_by_code.values()
        # Reset the warnings for the next check run
        self._warnings_by_code = {}

        for warning in messages:
            self.warning(warning)

    def _send_database_instance_metadata(self):
        if self.database_identifier not in self._database_instance_emitted:
            event = {
                "host": self.reported_hostname,
                "port": self._config.port,
                "database_instance": self.database_identifier,
                "database_hostname": self.database_hostname,
                "agent_version": datadog_agent.get_version(),
                "ddagenthostname": self.agent_hostname,
                "dbms": "mysql",
                "kind": "database_instance",
                "collection_interval": self._config.database_instance_collection_interval,
                'dbms_version': self.version.version + '+' + self.version.build,
                'integration_version': __version__,
                "tags": self.tag_manager.get_tags(),
                "timestamp": time.time() * 1000,
                "cloud_metadata": self._config.cloud_metadata,
                "metadata": {
                    "dbm": self._config.dbm_enabled,
                    "connection_host": self._config.host,
                },
            }
            self._database_instance_emitted[self.database_identifier] = event
            self.database_monitoring_metadata(json.dumps(event, default=default_json_event_encoding))

    def set_cluster_tags(self, db):
        if not self._config.replication_enabled:
            self.log.debug("Replication is not enabled, skipping cluster tags")
            return
        if self.is_mariadb:
            self.log.debug("MariaDB cluster tags are not currently supported")
            return
        if self._group_replication_active:
            self.log.debug("Group replication cluster tags are not currently supported")
            return

        replica_status = self._get_replica_replication_status(db)
        # Currently we only support single primary source clustering
        if replica_status and len(replica_status) > 0:
            self.cluster_uuid = replica_status[0].get('Source_UUID', replica_status[0].get('Master_UUID'))
            if self.cluster_uuid:
                self.tag_manager.set_tag('cluster_uuid', self.cluster_uuid, replace=True)
                self.tag_manager.set_tag('replication_role', "replica", replace=True)
                self._replication_role = "replica"
        else:
            if self.global_variables.log_bin_enabled:
                self.cluster_uuid = self.server_uuid
                self.tag_manager.set_tag('cluster_uuid', self.cluster_uuid, replace=True)
                self.tag_manager.set_tag('replication_role', "primary", replace=True)
                self._replication_role = "primary"
