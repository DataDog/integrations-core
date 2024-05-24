# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

import copy
import time
from collections import defaultdict

import six
from cachetools import TTLCache

from datadog_checks.base import AgentCheck
from datadog_checks.base.config import is_affirmative
from datadog_checks.base.utils.db import QueryExecutor, QueryManager
from datadog_checks.base.utils.db.utils import default_json_event_encoding, resolve_db_host, tracked_query
from datadog_checks.base.utils.serialization import json
from datadog_checks.sqlserver.activity import SqlserverActivity
from datadog_checks.sqlserver.config import SQLServerConfig
from datadog_checks.sqlserver.database_metrics import (
    SqlserverDatabaseBackupMetrics,
    SqlserverDBFragmentationMetrics,
    SqlserverIndexUsageMetrics,
)
from datadog_checks.sqlserver.metadata import SqlserverMetadata
from datadog_checks.sqlserver.statements import SqlserverStatementMetrics
from datadog_checks.sqlserver.stored_procedures import SqlserverProcedureMetrics
from datadog_checks.sqlserver.utils import Database, construct_use_statement, parse_sqlserver_major_version

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

from datadog_checks.sqlserver import metrics
from datadog_checks.sqlserver.__about__ import __version__
from datadog_checks.sqlserver.connection import Connection, SQLConnectionError, split_sqlserver_host_port
from datadog_checks.sqlserver.const import (
    AO_METRICS,
    AO_METRICS_PRIMARY,
    AO_METRICS_SECONDARY,
    AUTODISCOVERY_QUERY,
    AWS_RDS_HOSTNAME_SUFFIX,
    AZURE_DEPLOYMENT_TYPE_TO_RESOURCE_TYPES,
    BASE_NAME_QUERY,
    COUNTER_TYPE_QUERY,
    DATABASE_MASTER_FILES,
    DATABASE_METRICS,
    DATABASE_SERVICE_CHECK_NAME,
    DATABASE_SERVICE_CHECK_QUERY,
    DBM_MIGRATED_METRICS,
    ENGINE_EDITION_AZURE_MANAGED_INSTANCE,
    ENGINE_EDITION_SQL_DATABASE,
    INSTANCE_METRICS,
    INSTANCE_METRICS_DATABASE,
    INSTANCE_METRICS_NEWER_2016,
    PERF_AVERAGE_BULK,
    PERF_COUNTER_BULK_COUNT,
    PERF_COUNTER_LARGE_RAWCOUNT,
    PERF_LARGE_RAW_BASE,
    PERF_RAW_LARGE_FRACTION,
    SERVICE_CHECK_NAME,
    STATIC_INFO_ENGINE_EDITION,
    STATIC_INFO_MAJOR_VERSION,
    STATIC_INFO_VERSION,
    SWITCH_DB_STATEMENT,
    TASK_SCHEDULER_METRICS,
    TEMPDB_FILE_SPACE_USAGE_METRICS,
    VALID_METRIC_TYPES,
    expected_sys_databases_columns,
)
from datadog_checks.sqlserver.metrics import DEFAULT_PERFORMANCE_TABLE, VALID_TABLES
from datadog_checks.sqlserver.queries import (
    QUERY_AO_FAILOVER_CLUSTER,
    QUERY_AO_FAILOVER_CLUSTER_MEMBER,
    QUERY_FAILOVER_CLUSTER_INSTANCE,
    QUERY_LOG_SHIPPING_PRIMARY,
    QUERY_LOG_SHIPPING_SECONDARY,
    QUERY_SERVER_STATIC_INFO,
    get_query_ao_availability_groups,
    get_query_file_stats,
)
from datadog_checks.sqlserver.utils import (
    is_azure_database,
    is_azure_sql_database,
    set_default_driver_conf,
)

try:
    import adodbapi
except ImportError:
    adodbapi = None

try:
    import pyodbc
except ImportError:
    pyodbc = None

if adodbapi is None and pyodbc is None:
    raise ImportError("adodbapi or pyodbc must be installed to use this check.")

set_default_driver_conf()


class SQLServer(AgentCheck):
    __NAMESPACE__ = "sqlserver"

    def __init__(self, name, init_config, instances):
        super(SQLServer, self).__init__(name, init_config, instances)

        self._resolved_hostname = None
        self._agent_hostname = None
        self.connection = None
        self.failed_connections = {}
        self.instance_metrics = []
        self.instance_per_type_metrics = defaultdict(set)
        self.do_check = True

        self._config = SQLServerConfig(self.init_config, self.instance, self.log)
        self.tags = self._config.tags

        self.databases = set()
        self.autodiscovery_query = None
        self._ad_last_check = 0
        self._index_usage_last_check_ts = 0
        self._sql_counter_types = {}
        self.proc_type_mapping = {"gauge": self.gauge, "rate": self.rate, "histogram": self.histogram}

        # DBM
        self.statement_metrics = SqlserverStatementMetrics(self, self._config)
        self.procedure_metrics = SqlserverProcedureMetrics(self, self._config)
        self.sql_metadata = SqlserverMetadata(self, self._config)
        self.activity = SqlserverActivity(self, self._config)

        self.static_info_cache = TTLCache(
            maxsize=100,
            # cache these for a full day
            ttl=60 * 60 * 24,
        )
        # _database_instance_emitted: limit the collection and transmission of the database instance metadata
        self._database_instance_emitted = TTLCache(
            maxsize=1,
            ttl=self._config.database_instance_collection_interval,
        )  # type: TTLCache
        # Keep a copy of the tags before the internal resource tags are set so they can be used for paths that don't
        # go through the agent internal metrics submission processing those tags
        self._non_internal_tags = copy.deepcopy(self.tags)
        self.check_initializations.append(self.initialize_connection)
        self.check_initializations.append(self.set_resolved_hostname)
        self.check_initializations.append(self.set_resolved_hostname_metadata)
        self.check_initializations.append(self.config_checks)
        self.check_initializations.append(self.make_metric_list_to_collect)

        # Query declarations
        self._query_manager = None
        self._dynamic_queries = None  # DEPRECATED, new metrics should use database_metrics
        self.server_state_queries = None
        self.sqlserver_incr_fraction_metric_previous_values = {}

        self._database_metrics = None

    def cancel(self):
        self.statement_metrics.cancel()
        self.procedure_metrics.cancel()
        self.activity.cancel()
        self.sql_metadata.cancel()

    def config_checks(self):
        if self._config.autodiscovery and self.instance.get("database"):
            self.log.warning(
                "sqlserver `database_autodiscovery` and `database` options defined in same instance - "
                "autodiscovery will take precedence."
            )
        if not self._config.autodiscovery and (
            self._config.autodiscovery_include or self._config.autodiscovery_exclude
        ):
            self.log.warning(
                "Autodiscovery is disabled, autodiscovery_include and autodiscovery_exclude will be ignored"
            )

    def _new_query_executor(self, queries, executor, extra_tags=None, track_operation_time=False):
        tags = self.tags + (extra_tags or [])
        return QueryExecutor(
            executor,
            self,
            queries=queries,
            tags=tags,
            hostname=self.resolved_hostname,
            track_operation_time=track_operation_time,
        )

    def set_resolved_hostname_metadata(self):
        self.set_metadata("resolved_hostname", self.resolved_hostname)

    def set_resource_tags(self):
        if self._config.cloud_metadata.get("gcp") is not None:
            self.tags.append(
                "dd.internal.resource:gcp_sql_database_instance:{}:{}".format(
                    self._config.cloud_metadata.get("gcp")["project_id"],
                    self._config.cloud_metadata.get("gcp")["instance_id"],
                )
            )
        if self._config.cloud_metadata.get("aws") is not None:
            self.tags.append(
                "dd.internal.resource:aws_rds_instance:{}".format(
                    self._config.cloud_metadata.get("aws")["instance_endpoint"],
                )
            )
        elif AWS_RDS_HOSTNAME_SUFFIX in self._resolved_hostname:
            # allow for detecting if the host is an RDS host, and emit
            # the resource properly even if the `aws` config is unset
            self.tags.append("dd.internal.resource:aws_rds_instance:{}".format(self._resolved_hostname))
        if self._config.cloud_metadata.get("azure") is not None:
            deployment_type = self._config.cloud_metadata.get("azure")["deployment_type"]
            name = self._config.cloud_metadata.get("azure")["name"]
            db_instance = None
            if "sql_database" in deployment_type and self._config.dbm_enabled:
                # azure sql databases have a special format, which is set for DBM
                # customers in the resolved_hostname.
                # If user is not DBM customer, the resource_name should just be set to the `name`
                db_instance = self._resolved_hostname
            # some `deployment_type`s map to multiple `resource_type`s
            resource_types = AZURE_DEPLOYMENT_TYPE_TO_RESOURCE_TYPES.get(deployment_type).split(",")
            for r_type in resource_types:
                if "azure_sql_server_database" in r_type and db_instance:
                    self.tags.append("dd.internal.resource:{}:{}".format(r_type, db_instance))
                else:
                    self.tags.append("dd.internal.resource:{}:{}".format(r_type, name))
        # finally, emit a `database_instance` resource for this instance
        self.tags.append(
            "dd.internal.resource:database_instance:{}".format(
                self._resolved_hostname,
            )
        )

    def set_resolved_hostname(self):
        # load static information cache
        self.load_static_information()
        if self._resolved_hostname is None:
            if self._config.reported_hostname:
                self._resolved_hostname = self._config.reported_hostname
            else:
                host, _ = split_sqlserver_host_port(self.instance.get("host"))
                self._resolved_hostname = resolve_db_host(host)
                engine_edition = self.static_info_cache.get(STATIC_INFO_ENGINE_EDITION)
                if engine_edition == ENGINE_EDITION_SQL_DATABASE:
                    configured_database = self.instance.get("database", None)
                    if not configured_database:
                        configured_database = "master"
                        self.warning(
                            "Missing 'database' in instance configuration."
                            "For Azure SQL Database a non-master application database must be specified."
                        )
                    elif configured_database == "master":
                        self.warning(
                            "Wrong 'database' configured."
                            "For Azure SQL Database a non-master application database must be specified."
                        )
                    azure_server_suffix = ".database.windows.net"
                    if host.endswith(azure_server_suffix):
                        host = host[: -len(azure_server_suffix)]
                    # for Azure SQL Database, each database on a given "server" has isolated compute resources,
                    # meaning that the agent is only able to see query activity for the specific database it's
                    # connected to. For this reason, each Azure SQL database is modeled as an independent host.
                    self._resolved_hostname = "{}/{}".format(host, configured_database)
        # set resource tags to properly tag with updated hostname
        self.set_resource_tags()

    @property
    def resolved_hostname(self):
        return self._resolved_hostname

    def load_static_information(self):
        expected_keys = {STATIC_INFO_VERSION, STATIC_INFO_MAJOR_VERSION, STATIC_INFO_ENGINE_EDITION}
        missing_keys = expected_keys - set(self.static_info_cache.keys())
        if missing_keys:
            with self.connection.open_managed_default_connection():
                with self.connection.get_managed_cursor() as cursor:
                    if STATIC_INFO_VERSION not in self.static_info_cache:
                        cursor.execute("select @@version")
                        results = cursor.fetchall()
                        if results and len(results) > 0 and len(results[0]) > 0 and results[0][0]:
                            version = results[0][0]
                            self.static_info_cache[STATIC_INFO_VERSION] = version
                            self.static_info_cache[STATIC_INFO_MAJOR_VERSION] = parse_sqlserver_major_version(version)
                            if not self.static_info_cache[STATIC_INFO_MAJOR_VERSION]:
                                cursor.execute(
                                    "SELECT CAST(ServerProperty('ProductMajorVersion') AS INT) AS MajorVersion"
                                )
                                result = cursor.fetchone()
                                if result:
                                    self.static_info_cache[STATIC_INFO_MAJOR_VERSION] = result[0]
                                else:
                                    self.log.warning("failed to load version static information due to empty results")
                                self.log.warning("failed to parse SQL Server major version from version: %s", version)
                        else:
                            self.log.warning("failed to load version static information due to empty results")
                    if STATIC_INFO_ENGINE_EDITION not in self.static_info_cache:
                        cursor.execute("SELECT CAST(ServerProperty('EngineEdition') AS INT) AS Edition")
                        result = cursor.fetchone()
                        if result:
                            self.static_info_cache[STATIC_INFO_ENGINE_EDITION] = result[0]
                        else:
                            self.log.warning("failed to load version static information due to empty results")

            # re-initialize resolved_hostname to ensure we take into consideration the static information
            # after it's loaded
            self._resolved_hostname = None

    def debug_tags(self):
        return self.tags + ["agent_hostname:{}".format(self.agent_hostname)]

    def debug_stats_kwargs(self, tags=None):
        tags = tags if tags else []
        return {
            "tags": self.debug_tags() + tags,
            "hostname": self.resolved_hostname,
            "raw": True,
        }

    @property
    def agent_hostname(self):
        # type: () -> str
        if self._agent_hostname is None:
            self._agent_hostname = datadog_agent.get_hostname()
        return self._agent_hostname

    def initialize_connection(self):
        self.connection = Connection(
            host=self.resolved_hostname,
            init_config=self.init_config,
            instance_config=self.instance,
            service_check_handler=self.handle_service_check,
        )

    def make_metric_list_to_collect(self):
        # Pre-process the list of metrics to collect
        try:
            if self._config.ignore_missing_database:
                # self.connection.check_database() will try to connect to 'master'.
                # If this is an Azure SQL Database this function will throw.
                # For this reason we avoid calling self.connection.check_database()
                # for this config as it will be a false negative.
                engine_edition = self.static_info_cache.get(STATIC_INFO_ENGINE_EDITION)
                if not is_azure_sql_database(engine_edition):
                    # Do the database exist check that will allow to disable _check as a whole
                    # as otherwise the first call to open_managed_default_connection will throw the
                    # SQLConnectionError.
                    db_exists, context = self.connection.check_database()
                    if not db_exists:
                        self.do_check = False
                        self.log.warning("Database %s does not exist. Disabling checks for this instance.", context)
                        return
            if self.instance.get("stored_procedure") is None:
                with self.connection.open_managed_default_connection():
                    with self.connection.get_managed_cursor() as cursor:
                        self.autodiscover_databases(cursor)
                    self._make_metric_list_to_collect(self._config.custom_metrics)
        except SQLConnectionError:
            raise
        except Exception as e:
            self.log.exception("Initialization exception %s", e)

    def handle_service_check(self, status, connection_host, database, message=None, is_default=True):
        custom_tags = self.instance.get("tags", [])
        disable_generic_tags = self.instance.get("disable_generic_tags", False)
        service_check_tags = [
            "sqlserver_host:{}".format(self.resolved_hostname),
            "db:{}".format(database),
            "connection_host:{}".format(connection_host),
        ]
        if not disable_generic_tags:
            service_check_tags.append("host:{}".format(self.resolved_hostname))
        if custom_tags is not None:
            service_check_tags.extend(custom_tags)
        service_check_tags = list(set(service_check_tags))

        if status is AgentCheck.OK:
            message = None

        if is_default:
            self.service_check(SERVICE_CHECK_NAME, status, tags=service_check_tags, message=message, raw=True)
        if self._config.autodiscovery and self._config.autodiscovery_db_service_check:
            self.service_check(DATABASE_SERVICE_CHECK_NAME, status, tags=service_check_tags, message=message, raw=True)

    def autodiscover_databases(self, cursor):
        if not self._config.autodiscovery:
            return False

        now = time.time()
        if now - self._ad_last_check > self._config.autodiscovery_interval:
            self.log.info("Performing database autodiscovery")
            query = self._get_autodiscovery_query_cached(cursor)
            cursor.execute(query)
            rows = list(cursor.fetchall())
            if len(rows[0]) == 2:
                all_dbs = {Database(row.name, row.physical_database_name) for row in rows}
            else:
                all_dbs = {Database(row.name) for row in rows}
            excluded_dbs = {d for d in all_dbs if self._config._exclude_patterns.match(d.name)}
            included_dbs = {d for d in all_dbs if self._config._include_patterns.match(d.name)}

            self.log.debug(
                "Autodiscovered databases: %s, excluding: %s, including: %s", all_dbs, excluded_dbs, included_dbs
            )

            # keep included dbs but remove any that were explicitly excluded
            filtered_dbs = all_dbs.intersection(included_dbs) - excluded_dbs

            self.log.debug("Resulting filtered databases: %s", filtered_dbs)
            self._ad_last_check = now
            if filtered_dbs != self.databases:
                self.log.debug("Databases updated from previous autodiscovery check.")
                self.databases = filtered_dbs
                return True
        return False

    def _get_autodiscovery_query_cached(self, cursor):
        if self.autodiscovery_query:
            return self.autodiscovery_query
        available_columns = self._get_available_sys_database_columns(cursor, expected_sys_databases_columns)
        self.autodiscovery_query = AUTODISCOVERY_QUERY.format(columns=", ".join(available_columns))
        return self.autodiscovery_query

    def _get_available_sys_database_columns(self, cursor, all_expected_columns):
        # confirm that sys.databases has the expected columns as not all versions of sql server
        # support 'physical_database_name' column. The 'name' column will always be present &
        # will be returned as the first column in the autodiscovery query
        cursor.execute("select top 0 * from sys.databases")
        all_columns = {i[0] for i in cursor.description}
        available_columns = [c for c in all_expected_columns if c in all_columns]
        self.log.debug("found available sys.databases columns: %s", available_columns)
        return available_columns

    def _make_metric_list_to_collect(self, custom_metrics):
        """
        Store the list of metrics to collect by instance_key.
        Will also create and cache cursors to query the db.
        """

        major_version = self.static_info_cache.get(STATIC_INFO_MAJOR_VERSION)
        metrics_to_collect = []
        tags = self.instance.get("tags", [])

        # Load instance-level (previously Performance metrics)
        # If several check instances are querying the same server host, it can be wise to turn these off
        # to avoid sending duplicate metrics
        if is_affirmative(self.instance.get("include_instance_metrics", True)):
            common_metrics = list(INSTANCE_METRICS)
            if major_version and major_version >= 2016:
                common_metrics.extend(INSTANCE_METRICS_NEWER_2016)
            if not self._config.dbm_enabled:
                common_metrics.extend(DBM_MIGRATED_METRICS)
            if not self.databases:
                # if autodiscovery is enabled, we report metrics from the
                # INSTANCE_METRICS_DATABASE struct below, so do not double report here
                common_metrics.extend(INSTANCE_METRICS_DATABASE)
            self._add_performance_counters(common_metrics, metrics_to_collect, tags, db=None)

            # populated through autodiscovery
            if self.databases:
                for db in self.databases:
                    self._add_performance_counters(
                        INSTANCE_METRICS_DATABASE,
                        metrics_to_collect,
                        tags,
                        db=db.name,
                        physical_database_name=db.physical_db_name,
                    )

        # Load database statistics
        db_stats_to_collect = list(DATABASE_METRICS)
        engine_edition = self.static_info_cache.get(STATIC_INFO_ENGINE_EDITION)

        for name, table, column in db_stats_to_collect:
            # include database as a filter option
            db_names = [d.name for d in self.databases] or [
                self.instance.get("database", self.connection.DEFAULT_DATABASE)
            ]
            for db_name in db_names:
                cfg = {"name": name, "table": table, "column": column, "instance_name": db_name, "tags": tags}
                metrics_to_collect.append(self.typed_metric(cfg_inst=cfg, table=table, column=column))

        # Load AlwaysOn metrics
        if is_affirmative(self.instance.get("include_ao_metrics", False)):
            for name, table, column in AO_METRICS + AO_METRICS_PRIMARY + AO_METRICS_SECONDARY:
                db_name = "master"
                cfg = {
                    "name": name,
                    "table": table,
                    "column": column,
                    "instance_name": db_name,
                    "tags": tags,
                    "ao_database": self.instance.get("ao_database", None),
                    "availability_group": self.instance.get("availability_group", None),
                    "only_emit_local": is_affirmative(self.instance.get("only_emit_local", False)),
                }
                metrics_to_collect.append(self.typed_metric(cfg_inst=cfg, table=table, column=column))

        # Load metrics from scheduler and task tables, if enabled
        if is_affirmative(self.instance.get("include_task_scheduler_metrics", False)):
            for name, table, column in TASK_SCHEDULER_METRICS:
                cfg = {"name": name, "table": table, "column": column, "tags": tags}
                metrics_to_collect.append(self.typed_metric(cfg_inst=cfg, table=table, column=column))

        # Load sys.master_files metrics
        if is_affirmative(self.instance.get("include_master_files_metrics", False)):
            for name, table, column in DATABASE_MASTER_FILES:
                cfg = {"name": name, "table": table, "column": column, "tags": tags}
                metrics_to_collect.append(self.typed_metric(cfg_inst=cfg, table=table, column=column))

        # Load DB File Space Usage metrics
        if is_affirmative(
            self.instance.get("include_tempdb_file_space_usage_metrics", True)
        ) and not is_azure_sql_database(engine_edition):
            for name, table, column in TEMPDB_FILE_SPACE_USAGE_METRICS:
                cfg = {"name": name, "table": table, "column": column, "instance_name": "tempdb", "tags": tags}
                metrics_to_collect.append(self.typed_metric(cfg_inst=cfg, table=table, column=column))

        # Load any custom metrics from conf.d/sqlserver.yaml
        for cfg in custom_metrics:
            sql_counter_type = None
            base_name = None

            custom_tags = tags + cfg.get("tags", [])
            cfg["tags"] = custom_tags

            db_table = cfg.get("table", DEFAULT_PERFORMANCE_TABLE)
            if db_table not in VALID_TABLES:
                self.log.error("%s has an invalid table name: %s", cfg["name"], db_table)
                continue

            if cfg.get("database", None) and cfg.get("database") != self.instance.get("database"):
                self.log.debug(
                    "Skipping custom metric %s for database %s, check instance configured for database %s",
                    cfg["name"],
                    cfg.get("database"),
                    self.instance.get("database"),
                )
                continue

            if db_table == DEFAULT_PERFORMANCE_TABLE:
                user_type = cfg.get("type")
                if user_type is not None and user_type not in VALID_METRIC_TYPES:
                    self.log.error("%s has an invalid metric type: %s", cfg["name"], user_type)
                sql_counter_type = None
                try:
                    if user_type is None:
                        sql_counter_type, base_name = self.get_sql_counter_type(cfg["counter_name"])
                except Exception:
                    self.log.warning("Can't load the metric %s, ignoring", cfg["name"], exc_info=True)
                    continue

                metrics_to_collect.append(
                    self.typed_metric(
                        cfg_inst=cfg,
                        table=db_table,
                        base_name=base_name,
                        user_type=user_type,
                        sql_counter_type=sql_counter_type,
                    )
                )

            else:
                for column in cfg["columns"]:
                    metrics_to_collect.append(
                        self.typed_metric(
                            cfg_inst=cfg,
                            table=db_table,
                            base_name=base_name,
                            sql_counter_type=sql_counter_type,
                            column=column,
                        )
                    )

        self.instance_metrics = metrics_to_collect
        self.log.debug("metrics to collect %s", metrics_to_collect)

        # create an organized grouping of metric names to their metric classes
        for m in metrics_to_collect:
            cls = m.__class__.__name__
            name = m.sql_name or m.column
            self.log.debug("Adding metric class %s named %s", cls, name)

            self.instance_per_type_metrics[cls].add(name)
            if m.base_name:
                self.instance_per_type_metrics[cls].add(m.base_name)

    def _add_performance_counters(self, metrics, metrics_to_collect, tags, db=None, physical_database_name=None):
        if db is not None:
            tags = tags + ["database:{}".format(db)]
        for name, counter_name, instance_name, object_name in metrics:
            try:
                sql_counter_type, base_name = self.get_sql_counter_type(counter_name)
                cfg = {
                    "name": name,
                    "counter_name": counter_name,
                    "instance_name": db or instance_name,
                    "object_name": object_name,
                    "physical_db_name": physical_database_name,
                    "tags": tags,
                }

                metrics_to_collect.append(
                    self.typed_metric(
                        cfg_inst=cfg,
                        table=DEFAULT_PERFORMANCE_TABLE,
                        base_name=base_name,
                        sql_counter_type=sql_counter_type,
                    )
                )
            except SQLConnectionError:
                raise
            except Exception:
                self.log.warning("Can't load the metric %s, ignoring", name, exc_info=True)
                continue

    def get_sql_counter_type(self, counter_name):
        """
        Return the type of the performance counter so that we can report it to
        Datadog correctly
        If the sql_counter_type is one that needs a base (PERF_RAW_LARGE_FRACTION and
        PERF_AVERAGE_BULK), the name of the base counter will also be returned
        """
        cached = self._sql_counter_types.get(counter_name)
        if cached:
            return cached
        with self.connection.get_managed_cursor() as cursor:
            cursor.execute(COUNTER_TYPE_QUERY, (counter_name,))
            (sql_counter_type,) = cursor.fetchone()
            if sql_counter_type == PERF_LARGE_RAW_BASE:
                self.log.warning("Metric %s is of type Base and shouldn't be reported this way", counter_name)
            base_name = None
            if sql_counter_type in [PERF_AVERAGE_BULK, PERF_RAW_LARGE_FRACTION]:
                # This is an ugly hack. For certains type of metric (PERF_RAW_LARGE_FRACTION
                # and PERF_AVERAGE_BULK), we need two metrics: the metrics specified and
                # a base metrics to get the ratio. There is no unique schema, so we generate
                # the possible candidates, and we look at which ones exist in the db.
                counter_name_lowercase = counter_name.lower()
                # lowercase is used to avoid case sensitivity issues such as base vs. Base or BASE
                candidates = (
                    counter_name_lowercase + " base",
                    counter_name_lowercase.replace("(ms)", "base"),
                    counter_name_lowercase.replace("avg ", "") + " base",
                )
                try:
                    cursor.execute(BASE_NAME_QUERY, candidates)
                    row = cursor.fetchone()
                    if row:
                        base_name = row.counter_name.strip()
                        self.log.debug("Got base metric: %s for metric: %s", base_name, counter_name)
                        self._sql_counter_types[counter_name] = (sql_counter_type, base_name)
                    else:
                        self.log.warning(
                            "Could not get counter_name of base for metric %s with candidates %s",
                            counter_name,
                            candidates,
                        )
                except Exception as e:
                    self.log.warning("Could not get counter_name of base for metric: %s", e)

        return sql_counter_type, base_name

    def typed_metric(self, cfg_inst, table, base_name=None, user_type=None, sql_counter_type=None, column=None):
        """
        Create the appropriate BaseSqlServerMetric object, each implementing its method to
        fetch the metrics properly.
        If a `type` was specified in the config, it is used to report the value
        directly fetched from SQLServer. Otherwise, it is decided based on the
        sql_counter_type, according to microsoft's documentation.
        """
        if table == DEFAULT_PERFORMANCE_TABLE:
            metric_type_mapping = {
                PERF_COUNTER_BULK_COUNT: (self.rate, metrics.SqlSimpleMetric),
                PERF_COUNTER_LARGE_RAWCOUNT: (self.gauge, metrics.SqlSimpleMetric),
                PERF_LARGE_RAW_BASE: (self.gauge, metrics.SqlSimpleMetric),
                PERF_RAW_LARGE_FRACTION: (self.gauge, metrics.SqlFractionMetric),
                PERF_AVERAGE_BULK: (self.gauge, metrics.SqlIncrFractionMetric),
            }
            if user_type is not None:
                # user type overrides any other value
                metric_type = getattr(self, user_type)
                cls = metrics.SqlSimpleMetric

            else:
                metric_type, cls = metric_type_mapping[sql_counter_type]
        else:
            # Lookup metrics classes by their associated table
            metric_type_str, cls = metrics.TABLE_MAPPING[table]
            metric_type = getattr(self, metric_type_str)

        cfg_inst["hostname"] = self.resolved_hostname

        return cls(cfg_inst, base_name, metric_type, column, self.log)

    def _check_connections_by_connecting_to_db(self):
        for db in self.databases:
            if db.name != self.connection.DEFAULT_DATABASE:
                try:
                    self.connection.check_database_conns(db.name)
                except Exception as e:
                    # service_check errors on auto discovered databases should not abort the check
                    self.log.warning("failed service check for auto discovered database: %s", e)

    def _check_connections_by_use_db(self):
        with self.connection.open_managed_default_connection():
            with self.connection.get_managed_cursor() as cursor:
                for db in self.databases:
                    check_err_message = "Database {} connection service check failed: {}"
                    try:
                        cursor.execute(SWITCH_DB_STATEMENT.format(db.name))
                        cursor.execute(DATABASE_SERVICE_CHECK_QUERY)
                        cursor.fetchall()
                        self.handle_service_check(AgentCheck.OK, self.connection.get_host_with_port(), db.name, False)
                    except Exception as e:
                        self.log.warning(check_err_message.format(db.name, str(e)))
                        self.handle_service_check(
                            AgentCheck.CRITICAL,
                            self.connection.get_host_with_port(),
                            db.name,
                            check_err_message.format(db.name, str(e)),
                            False,
                        )
                        continue
                # Switch DB back to MASTER
                cursor.execute(SWITCH_DB_STATEMENT.format(self.connection.DEFAULT_DATABASE))

    def _check_database_conns(self):
        engine_edition = self.static_info_cache.get(STATIC_INFO_ENGINE_EDITION)
        if is_azure_sql_database(engine_edition):
            # On Azure, we can't use a less costly approach.
            self._check_connections_by_connecting_to_db()
        else:
            self._check_connections_by_use_db()

    def check(self, _):
        if self.do_check:
            # configure custom queries for the check
            if self._query_manager is None:
                # use QueryManager to process custom queries
                self._query_manager = QueryManager(
                    self, self.execute_query_raw, tags=self.tags, hostname=self.resolved_hostname
                )
                self._query_manager.compile_queries()
            if self.server_state_queries is None:
                self.server_state_queries = self._new_query_executor(
                    [QUERY_SERVER_STATIC_INFO], executor=self.execute_query_raw
                )
                self.server_state_queries.compile_queries()
            if self._config.proc:
                self.do_stored_procedure_check()
            else:
                self.collect_metrics()
            if self._config.autodiscovery and self._config.autodiscovery_db_service_check:
                self._check_database_conns()
            self._send_database_instance_metadata()
            if self._config.dbm_enabled:
                self.statement_metrics.run_job_loop(self.tags)
                self.procedure_metrics.run_job_loop(self.tags)
                self.activity.run_job_loop(self.tags)
                self.sql_metadata.run_job_loop(self.tags)
        else:
            self.log.debug("Skipping check")

    @property
    def dynamic_queries(self):
        """
        Initializes dynamic queries which depend on static information loaded from the database
        """
        if self._dynamic_queries:
            return self._dynamic_queries

        major_version = self.static_info_cache.get(STATIC_INFO_MAJOR_VERSION)
        engine_edition = self.static_info_cache.get(STATIC_INFO_ENGINE_EDITION)
        # need either major_version or engine_edition to generate queries
        if not major_version and not is_azure_database(engine_edition):
            self.log.warning("missing major_version, cannot initialize dynamic queries")
            return None
        queries = [get_query_file_stats(major_version, engine_edition)]

        if is_affirmative(self.instance.get("include_ao_metrics", False)):
            if major_version > 2012 or is_azure_database(engine_edition):
                queries.extend(
                    [
                        get_query_ao_availability_groups(major_version),
                        QUERY_AO_FAILOVER_CLUSTER,
                        QUERY_AO_FAILOVER_CLUSTER_MEMBER,
                    ]
                )
            else:
                self.log_missing_metric("AlwaysOn", major_version, engine_edition)
        if is_affirmative(self.instance.get("include_fci_metrics", False)):
            if major_version > 2012 or engine_edition == ENGINE_EDITION_AZURE_MANAGED_INSTANCE:
                queries.extend([QUERY_FAILOVER_CLUSTER_INSTANCE])
            else:
                self.log_missing_metric("Failover Cluster Instance", major_version, engine_edition)

        if is_affirmative(self.instance.get("include_primary_log_shipping_metrics", False)):
            queries.extend([QUERY_LOG_SHIPPING_PRIMARY])

        if is_affirmative(self.instance.get("include_secondary_log_shipping_metrics", False)):
            queries.extend([QUERY_LOG_SHIPPING_SECONDARY])

        self._dynamic_queries = self._new_query_executor(queries, executor=self.execute_query_raw)
        self._dynamic_queries.compile_queries()
        self.log.debug("initialized dynamic queries")
        return self._dynamic_queries

    @property
    def database_metrics(self):
        """
        Initializes database metrics which depend on static information loaded from the database
        """
        if self._database_metrics:
            return self._database_metrics

        # list of database names to collect metrics for
        db_names = [d.name for d in self.databases] or [self.instance.get("database", self.connection.DEFAULT_DATABASE)]

        # instance level metrics
        database_backup_metrics = SqlserverDatabaseBackupMetrics(
            instance_config=self.instance,
            new_query_executor=self._new_query_executor,
            server_static_info=self.static_info_cache,
            execute_query_handler=self.execute_query_raw,
        )

        # database level metrics
        index_usage_metrics = SqlserverIndexUsageMetrics(
            instance_config=self.instance,
            new_query_executor=self._new_query_executor,
            server_static_info=self.static_info_cache,
            execute_query_handler=self.execute_query_raw,
            databases=db_names,
        )
        db_fragmentation_metrics = SqlserverDBFragmentationMetrics(
            instance_config=self.instance,
            new_query_executor=self._new_query_executor,
            server_static_info=self.static_info_cache,
            execute_query_handler=self.execute_query_raw,
            databases=db_names,
        )

        # create a list of dynamic queries to execute
        self._database_metrics = [
            # instance level metrics
            database_backup_metrics,
            # database level metrics
            index_usage_metrics,
            db_fragmentation_metrics,
        ]
        self.log.debug("initialized dynamic queries")
        return self._database_metrics

    def log_missing_metric(self, metric_name, major_version, engine_version):
        if major_version <= 2012:
            self.log.warning("%s metrics are not supported on version 2012", metric_name)
        else:
            self.log.warning("%s metrics are not supported on Azure engine version: %s", metric_name, engine_version)

    def collect_metrics(self):
        """Fetch the metrics from all the associated database tables."""

        with self.connection.open_managed_default_connection():
            with self.connection.get_managed_cursor() as cursor:
                # initiate autodiscovery or if the server was down at check __init__ key could be missing.
                if self.autodiscover_databases(cursor) or not self.instance_metrics:
                    self._make_metric_list_to_collect(self._config.custom_metrics)

                instance_results = {}
                engine_edition = self.static_info_cache.get(STATIC_INFO_ENGINE_EDITION, "")
                # Execute the `fetch_all` operations first to minimize the database calls
                for cls, metric_names in six.iteritems(self.instance_per_type_metrics):
                    if not metric_names:
                        instance_results[cls] = None, None
                    else:
                        try:
                            db_names = [d.name for d in self.databases] or [
                                self.instance.get("database", self.connection.DEFAULT_DATABASE)
                            ]
                            metric_cls = getattr(metrics, cls)
                            with tracked_query(self, operation=metric_cls.OPERATION_NAME):
                                rows, cols = metric_cls.fetch_all_values(
                                    cursor,
                                    list(metric_names),
                                    self.log,
                                    databases=db_names,
                                    engine_edition=engine_edition,
                                )
                        except Exception as e:
                            self.log.error("Error running `fetch_all` for metrics %s - skipping.  Error: %s", cls, e)
                            rows, cols = None, None

                        instance_results[cls] = rows, cols

                for metric in self.instance_metrics:
                    key = metric.__class__.__name__
                    if key not in instance_results:
                        self.log.warning("No %s metrics found, skipping", str(key))
                    else:
                        rows, cols = instance_results[key]
                        if rows is not None:
                            if key == "SqlIncrFractionMetric":
                                metric.fetch_metric(rows, cols, self.sqlserver_incr_fraction_metric_previous_values)
                            else:
                                metric.fetch_metric(rows, cols)

            # Neither pyodbc nor adodbapi are able to read results of a query if the number of rows affected
            # statement are returned as part of the result set, so we disable for the entire connection
            # this is important mostly for custom_queries or the stored_procedure feature
            # https://docs.microsoft.com/en-us/sql/t-sql/statements/set-nocount-transact-sql
            with self.connection.get_managed_cursor() as cursor:
                cursor.execute("SET NOCOUNT ON")
            try:
                # Server state queries require VIEW SERVER STATE permissions, which some managed database
                # versions do not support.
                if self.static_info_cache.get(STATIC_INFO_ENGINE_EDITION) not in [
                    ENGINE_EDITION_SQL_DATABASE,
                ]:
                    self.server_state_queries.execute()

                if self.dynamic_queries:
                    self.dynamic_queries.execute()

                # restore the current database after executing dynamic queries
                # this is to ensure the current database context is not changed
                with self.connection.restore_current_database_context():
                    if self.database_metrics:
                        for database_metric in self.database_metrics:
                            database_metric.execute()

                # reuse connection for any custom queries
                self._query_manager.execute()
            finally:
                with self.connection.get_managed_cursor() as cursor:
                    cursor.execute("SET NOCOUNT OFF")

    def execute_query_raw(self, query, db=None):
        with self.connection.get_managed_cursor() as cursor:
            if db:
                ctx = construct_use_statement(db)
                self.log.debug("changing cursor context via use statement: %s", ctx)
                cursor.execute(ctx)
            cursor.execute(query)
            return cursor.fetchall()

    def do_stored_procedure_check(self):
        """
        Fetch the metrics from the stored proc
        """

        proc = self._config.proc
        guardSql = self.instance.get("proc_only_if")
        custom_tags = self.instance.get("tags", [])

        if (guardSql and self.proc_check_guard(guardSql)) or not guardSql:
            self.connection.open_db_connections(self.connection.DEFAULT_DB_KEY)
            cursor = self.connection.get_cursor(self.connection.DEFAULT_DB_KEY)

            try:
                self.log.debug("Calling Stored Procedure : %s", proc)
                if self.connection.connector == "adodbapi":
                    cursor.callproc(proc)
                else:
                    # pyodbc does not support callproc; use execute instead.
                    # Reference: https://github.com/mkleehammer/pyodbc/wiki/Calling-Stored-Procedures
                    call_proc = "{{CALL {}}}".format(proc)
                    cursor.execute(call_proc)

                rows = cursor.fetchall()
                self.log.debug("Row count (%s) : %s", proc, cursor.rowcount)

                for row in rows:
                    tags = [] if row.tags is None or row.tags == "" else row.tags.split(",")
                    tags.extend(custom_tags)

                    if row.type.lower() in self.proc_type_mapping:
                        self.proc_type_mapping[row.type](row.metric, row.value, tags, raw=True)
                    else:
                        self.log.warning(
                            "%s is not a recognised type from procedure %s, metric %s", row.type, proc, row.metric
                        )

            except Exception as e:
                self.log.warning("Could not call procedure %s: %s", proc, e)
                raise e

            self.connection.close_cursor(cursor)
            self.connection.close_db_connections(self.connection.DEFAULT_DB_KEY)
        else:
            self.log.info("Skipping call to %s due to only_if", proc)

    def proc_check_guard(self, sql):
        """
        check to see if the guard SQL returns a single column containing 0 or 1
        We return true if 1, else False
        """
        self.connection.open_db_connections(self.connection.PROC_GUARD_DB_KEY)
        cursor = self.connection.get_cursor(self.connection.PROC_GUARD_DB_KEY)

        should_run = False
        try:
            cursor.execute(sql, ())
            result = cursor.fetchone()
            should_run = result[0] == 1
        except Exception as e:
            self.log.error("Failed to run proc_only_if sql %s : %s", sql, e)

        self.connection.close_cursor(cursor)
        self.connection.close_db_connections(self.connection.PROC_GUARD_DB_KEY)
        return should_run

    def _send_database_instance_metadata(self):
        if self.resolved_hostname not in self._database_instance_emitted:
            event = {
                "host": self.resolved_hostname,
                "agent_version": datadog_agent.get_version(),
                "dbms": "sqlserver",
                "kind": "database_instance",
                "collection_interval": self._config.database_instance_collection_interval,
                "dbms_version": "{},{}".format(
                    self.static_info_cache.get(STATIC_INFO_VERSION, ""),
                    self.static_info_cache.get(STATIC_INFO_ENGINE_EDITION, ""),
                ),
                "integration_version": __version__,
                "tags": self._non_internal_tags,
                "timestamp": time.time() * 1000,
                "cloud_metadata": self._config.cloud_metadata,
                "metadata": {
                    "dbm": self._config.dbm_enabled,
                    "connection_host": self._config.connection_host,
                },
            }
            self._database_instance_emitted[self.resolved_hostname] = event
            self.database_monitoring_metadata(json.dumps(event, default=default_json_event_encoding))
