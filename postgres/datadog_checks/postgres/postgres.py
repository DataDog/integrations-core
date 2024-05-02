# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import contextlib
import copy
import functools
import os
from time import time

import psycopg2
from cachetools import TTLCache
from six import iteritems

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.db import QueryExecutor
from datadog_checks.base.utils.db.utils import (
    default_json_event_encoding,
    tracked_query,
)
from datadog_checks.base.utils.db.utils import resolve_db_host as agent_host_resolver
from datadog_checks.base.utils.serialization import json
from datadog_checks.postgres import aws, azure
from datadog_checks.postgres.connections import MultiDatabaseConnectionPool
from datadog_checks.postgres.cursor import CommenterCursor, CommenterDictCursor
from datadog_checks.postgres.discovery import PostgresAutodiscovery
from datadog_checks.postgres.metadata import PostgresMetadata
from datadog_checks.postgres.metrics_cache import PostgresMetricsCache
from datadog_checks.postgres.relationsmanager import (
    DYNAMIC_RELATION_QUERIES,
    INDEX_BLOAT,
    RELATION_METRICS,
    TABLE_BLOAT,
    RelationsManager,
)
from datadog_checks.postgres.statement_samples import PostgresStatementSamples
from datadog_checks.postgres.statements import PostgresStatementMetrics

from .__about__ import __version__
from .config import PostgresConfig
from .util import (
    ANALYZE_PROGRESS_METRICS,
    AWS_RDS_HOSTNAME_SUFFIX,
    AZURE_DEPLOYMENT_TYPE_TO_RESOURCE_TYPE,
    CLUSTER_VACUUM_PROGRESS_METRICS,
    CONNECTION_METRICS,
    COUNT_METRICS,
    FUNCTION_METRICS,
    INDEX_PROGRESS_METRICS,
    QUERY_PG_CONTROL_CHECKPOINT,
    QUERY_PG_REPLICATION_SLOTS,
    QUERY_PG_REPLICATION_SLOTS_STATS,
    QUERY_PG_STAT_DATABASE,
    QUERY_PG_STAT_DATABASE_CONFLICTS,
    QUERY_PG_STAT_WAL_RECEIVER,
    QUERY_PG_UPTIME,
    REPLICATION_METRICS,
    SLRU_METRICS,
    SNAPSHOT_TXID_METRICS,
    SNAPSHOT_TXID_METRICS_LT_13,
    STAT_SUBSCRIPTION_METRICS,
    STAT_SUBSCRIPTION_STATS_METRICS,
    STAT_WAL_METRICS,
    SUBSCRIPTION_STATE_METRICS,
    VACUUM_PROGRESS_METRICS,
    WAL_FILE_METRICS,
    DatabaseConfigurationError,
    DatabaseHealthCheckError,  # noqa: F401
    fmt,
    get_schema_field,
    payload_pg_version,
    warning_with_tags,
)
from .version_utils import V9, V9_2, V10, V12, V13, V14, V15, VersionUtils

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

MAX_CUSTOM_RESULTS = 100

PG_SETTINGS_QUERY = "SELECT name, setting FROM pg_settings WHERE name IN (%s, %s, %s)"


class PostgreSql(AgentCheck):
    """Collects per-database, and optionally per-relation metrics, custom metrics"""

    SOURCE_TYPE_NAME = 'postgresql'
    SERVICE_CHECK_NAME = 'postgres.can_connect'
    METADATA_TRANSFORMERS = {'version': VersionUtils.transform_version}

    def __init__(self, name, init_config, instances):
        super(PostgreSql, self).__init__(name, init_config, instances)
        self._resolved_hostname = None
        self._agent_hostname = None
        self._db = None
        self.version = None
        self.raw_version = None
        self.system_identifier = None
        self.is_aurora = None
        self._version_utils = VersionUtils()
        # Deprecate custom_metrics in favor of custom_queries
        if 'custom_metrics' in self.instance:
            self.warning(
                "DEPRECATION NOTICE: Please use the new custom_queries option "
                "rather than the now deprecated custom_metrics"
            )
        if 'managed_identity' in self.instance:
            self.warning(
                "DEPRECATION NOTICE: The managed_identity option is deprecated and will be removed in a future version."
                " Please use the new azure.managed_authentication option instead."
            )
        self._config = PostgresConfig(self.instance, self.init_config)
        self.cloud_metadata = self._config.cloud_metadata
        self.tags = self._config.tags
        # Keep a copy of the tags without the internal resource tags so they can be used for paths that don't
        # go through the agent internal metrics submission processing those tags
        self._non_internal_tags = copy.deepcopy(self.tags)
        self.set_resource_tags()
        self.pg_settings = {}
        self._warnings_by_code = {}
        self.db_pool = MultiDatabaseConnectionPool(self._new_connection, self._config.max_connections)
        self.metrics_cache = PostgresMetricsCache(self._config)
        self.statement_metrics = PostgresStatementMetrics(self, self._config, shutdown_callback=self._close_db_pool)
        self.statement_samples = PostgresStatementSamples(self, self._config, shutdown_callback=self._close_db_pool)
        self.metadata_samples = PostgresMetadata(self, self._config, shutdown_callback=self._close_db_pool)
        self._relations_manager = RelationsManager(self._config.relations, self._config.max_relations)
        self._clean_state()
        self.check_initializations.append(lambda: RelationsManager.validate_relations_config(self._config.relations))
        self.check_initializations.append(self.set_resolved_hostname_metadata)
        self.check_initializations.append(self._connect)
        self.check_initializations.append(self.load_version)
        self.check_initializations.append(self.initialize_is_aurora)
        self.tags_without_db = [t for t in copy.copy(self.tags) if not t.startswith("db:")]
        self.autodiscovery = self._build_autodiscovery()
        self._dynamic_queries = []
        # _database_instance_emitted: limit the collection and transmission of the database instance metadata
        self._database_instance_emitted = TTLCache(
            maxsize=1,
            ttl=self._config.database_instance_collection_interval,
        )  # type: TTLCache

    def _build_autodiscovery(self):
        if not self._config.discovery_config['enabled']:
            return None

        if not self._config.relations:
            self.log.warning(
                "Database autodiscovery is enabled, but relation-level metrics are not being collected."
                "All metrics will be gathered from global view, and autodiscovery will not run."
            )
            return None

        discovery = PostgresAutodiscovery(
            self,
            'postgres',
            self._config.discovery_config,
            self._config.idle_connection_timeout,
        )
        return discovery

    def set_resource_tags(self):
        if self.cloud_metadata.get("gcp") is not None:
            self.tags.append(
                "dd.internal.resource:gcp_sql_database_instance:{}:{}".format(
                    self.cloud_metadata.get("gcp")["project_id"], self.cloud_metadata.get("gcp")["instance_id"]
                )
            )
        if self.cloud_metadata.get("aws") is not None and 'instance_endpoint' in self.cloud_metadata.get("aws"):
            self.tags.append(
                "dd.internal.resource:aws_rds_instance:{}".format(
                    self.cloud_metadata.get("aws")["instance_endpoint"],
                )
            )
        elif AWS_RDS_HOSTNAME_SUFFIX in self.resolved_hostname:
            # allow for detecting if the host is an RDS host, and emit
            # the resource properly even if the `aws` config is unset
            self.tags.append("dd.internal.resource:aws_rds_instance:{}".format(self.resolved_hostname))
        if self.cloud_metadata.get("azure") is not None:
            deployment_type = self.cloud_metadata.get("azure")["deployment_type"]
            # some `deployment_type`s map to multiple `resource_type`s
            resource_type = AZURE_DEPLOYMENT_TYPE_TO_RESOURCE_TYPE.get(deployment_type)
            if resource_type:
                self.tags.append(
                    "dd.internal.resource:{}:{}".format(resource_type, self.cloud_metadata.get("azure")["name"])
                )
        # finally, emit a `database_instance` resource for this instance
        self.tags.append(
            "dd.internal.resource:database_instance:{}".format(
                self.resolved_hostname,
            )
        )

    def _new_query_executor(self, queries, db):
        return QueryExecutor(
            functools.partial(self.execute_query_raw, db=db),
            self,
            queries=queries,
            tags=self.tags_without_db,
            hostname=self.resolved_hostname,
            track_operation_time=True,
        )

    def execute_query_raw(self, query, db):
        with db() as conn:
            with conn.cursor(cursor_factory=CommenterCursor) as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
                return rows

    @contextlib.contextmanager
    def db(self):
        """
        db context manager that yields a healthy connection to the main database
        """
        if not self._db or self._db.closed:
            # if the connection is closed, we need to reinitialize the connection
            self._db = self._new_connection(self._config.dbname)
            # once the connection is reinitialized, we need to reload the pg_settings
            self._load_pg_settings(self._db)
        if self._db.status != psycopg2.extensions.STATUS_READY:
            self._db.rollback()
        try:
            yield self._db
        except (psycopg2.InterfaceError, InterruptedError):
            # if we get an interface error or an interrupted error,
            # we gracefully close the connection
            self.log.warning(
                "Connection to the database %s has been interrupted, closing connection", self._config.dbname
            )
            try:
                self._db.close()
            except Exception:
                pass
            finally:
                self._db = None
            raise
        except Exception:
            self.log.exception("Unhandled exception while using database connection %s", self._config.dbname)
            raise

    def _connection_health_check(self, conn):
        try:
            # run a simple query to check if the connection is healthy
            # health check should run after a connection is established
            with conn.cursor(cursor_factory=CommenterCursor) as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchall()
        except psycopg2.OperationalError as e:
            err_msg = f"Database {self._config.dbname} connection health check failed: {str(e)}"
            self.log.error(err_msg)
            raise DatabaseHealthCheckError(err_msg)

    @property
    def dynamic_queries(self):
        if self._dynamic_queries:
            return self._dynamic_queries

        if self.version is None:
            self.log.debug("Version set to None due to incorrect identified version, aborting dynamic queries")
            return None

        self.log.debug("Generating dynamic queries")
        queries = []
        per_database_queries = []  # queries that need to be run per database, used for autodiscovery
        if self.version >= V9_2:
            q_pg_stat_database = copy.deepcopy(QUERY_PG_STAT_DATABASE)
            if len(self._config.ignore_databases) > 0:
                q_pg_stat_database["query"] += " WHERE " + " AND ".join(
                    "datname not ilike '{}'".format(db) for db in self._config.ignore_databases
                )
            q_pg_stat_database_conflicts = copy.deepcopy(QUERY_PG_STAT_DATABASE_CONFLICTS)
            if len(self._config.ignore_databases) > 0:
                q_pg_stat_database_conflicts["query"] += " WHERE " + " AND ".join(
                    "datname not ilike '{}'".format(db) for db in self._config.ignore_databases
                )

            if self._config.dbstrict and len(self._config.ignore_databases) == 0:
                q_pg_stat_database["query"] += " WHERE datname in('{}')".format(self._config.dbname)
                q_pg_stat_database_conflicts["query"] += " WHERE datname in('{}')".format(self._config.dbname)
            elif self._config.dbstrict and len(self._config.ignore_databases) > 0:
                q_pg_stat_database["query"] += " AND datname in('{}')".format(self._config.dbname)
                q_pg_stat_database_conflicts["query"] += " AND datname in('{}')".format(self._config.dbname)

            queries.extend(
                [
                    q_pg_stat_database,
                    q_pg_stat_database_conflicts,
                    QUERY_PG_UPTIME,
                    QUERY_PG_CONTROL_CHECKPOINT,
                ]
            )

        if self.version >= V10:
            # Wal receiver is not supported on aurora
            # select * from pg_stat_wal_receiver;
            # ERROR:  Function pg_stat_get_wal_receiver() is currently not supported in Aurora
            if self.is_aurora is False:
                queries.append(QUERY_PG_STAT_WAL_RECEIVER)
                if self._config.collect_wal_metrics is not False:
                    # collect wal metrics for pg >= 10 only if the user has not explicitly disabled it
                    queries.append(WAL_FILE_METRICS)
            queries.append(QUERY_PG_REPLICATION_SLOTS)
            queries.append(VACUUM_PROGRESS_METRICS)
            queries.append(STAT_SUBSCRIPTION_METRICS)

        if self.version >= V12:
            queries.append(CLUSTER_VACUUM_PROGRESS_METRICS)
            queries.append(INDEX_PROGRESS_METRICS)

        if self.version >= V13:
            queries.append(ANALYZE_PROGRESS_METRICS)
            queries.append(SNAPSHOT_TXID_METRICS)
        if self.version < V13:
            queries.append(SNAPSHOT_TXID_METRICS_LT_13)
        if self.version >= V14:
            if self.is_aurora is False:
                queries.append(STAT_WAL_METRICS)
            queries.append(QUERY_PG_REPLICATION_SLOTS_STATS)
            queries.append(SUBSCRIPTION_STATE_METRICS)
        if self.version >= V15:
            queries.append(STAT_SUBSCRIPTION_STATS_METRICS)

        if not queries:
            self.log.debug("no dynamic queries defined")
            return None

        # Dynamic queries for relationsmanager
        if self._config.relations:
            for query in DYNAMIC_RELATION_QUERIES:
                query = copy.copy(query)
                formatted_query = self._relations_manager.filter_relation_query(query['query'], 'nspname')
                query['query'] = formatted_query
                per_database_queries.append(query)

        if self.autodiscovery:
            self._collect_dynamic_queries_autodiscovery(per_database_queries)
        else:
            queries.extend(per_database_queries)
        self._dynamic_queries.append(self._new_query_executor(queries, db=self.db))
        for dynamic_query in self._dynamic_queries:
            dynamic_query.compile_queries()
        self.log.debug("initialized %s dynamic querie(s)", len(queries))

        return self._dynamic_queries

    def cancel(self):
        """
        Cancels and sends cancel signal to all threads.
        """
        if self._config.dbm_enabled:
            self.statement_samples.cancel()
            self.statement_metrics.cancel()
            self.metadata_samples.cancel()
        self._close_db_pool()
        if self._db:
            self._db.close()

    def _clean_state(self):
        self.log.debug("Cleaning state")
        self.metrics_cache.clean_state()
        self._dynamic_queries = []

    def _get_debug_tags(self):
        return ['agent_hostname:{}'.format(self.agent_hostname)]

    def _get_replication_role(self):
        with self.db() as conn:
            with conn.cursor(cursor_factory=CommenterCursor) as cursor:
                cursor.execute('SELECT pg_is_in_recovery();')
                role = cursor.fetchone()[0]
                # value fetched for role is of <type 'bool'>
                return "standby" if role else "master"

    def _collect_wal_metrics(self):
        if self.version >= V10:
            # _collect_stats will gather wal file metrics
            # for PG >= V10
            return
        wal_file_age = self._get_local_wal_file_age()
        if wal_file_age is not None:
            self.gauge(
                "postgresql.wal_age",
                wal_file_age,
                tags=self.tags_without_db,
                hostname=self.resolved_hostname,
            )

    def _get_local_wal_file_age(self):
        wal_log_dir = os.path.join(self._config.data_directory, "pg_xlog")
        if not os.path.isdir(wal_log_dir):
            self.log.warning(
                "Cannot access WAL log directory: %s. Ensure that you are "
                "running the agent on your local postgres database.",
                wal_log_dir,
            )
            return None

        all_dir_contents = os.listdir(wal_log_dir)
        all_files = [f for f in all_dir_contents if os.path.isfile(os.path.join(wal_log_dir, f))]

        # files extensions that are not valid WAL files
        exluded_file_exts = [".backup", ".history"]
        all_wal_files = [
            os.path.join(wal_log_dir, file_name)
            for file_name in all_files
            if not any(ext for ext in exluded_file_exts if file_name.endswith(ext))
        ]
        if len(all_wal_files) < 1:
            self.log.warning("No WAL files found in directory: %s.", wal_log_dir)
            return None

        oldest_file = min(all_wal_files, key=os.path.getctime)
        now = time()
        oldest_file_age = now - os.path.getctime(oldest_file)
        return oldest_file_age

    def load_system_identifier(self):
        with self.db() as conn:
            with conn.cursor(cursor_factory=CommenterCursor) as cursor:
                cursor.execute('SELECT system_identifier FROM pg_control_system();')
                self.system_identifier = cursor.fetchone()[0]

    def load_version(self):
        self.raw_version = self._version_utils.get_raw_version(self.db())
        self.version = self._version_utils.parse_version(self.raw_version)
        self.set_metadata('version', self.raw_version)

    def initialize_is_aurora(self):
        if self.is_aurora is None:
            self.is_aurora = self._version_utils.is_aurora(self.db())
        return self.is_aurora

    @property
    def resolved_hostname(self):
        # type: () -> str
        if self._resolved_hostname is None:
            if self._config.reported_hostname:
                self._resolved_hostname = self._config.reported_hostname
            else:
                self._resolved_hostname = self.resolve_db_host()
        return self._resolved_hostname

    def set_resolved_hostname_metadata(self):
        """
        set_resolved_hostname_metadata cannot be invoked in the __init__ method because it calls self.set_metadata.
        self.set_metadata can only be called successfully after the __init__ method has completed because
        it relies on the metadata manager, which in turn relies on having a check_id set. The Agent only
        sets the check_id after initialization has completed.
        """
        self.set_metadata('resolved_hostname', self._resolved_hostname)

    @property
    def agent_hostname(self):
        # type: () -> str
        if self._agent_hostname is None:
            self._agent_hostname = datadog_agent.get_hostname()
        return self._agent_hostname

    def resolve_db_host(self):
        return agent_host_resolver(self._config.host)

    def _run_query_scope(self, cursor, scope, is_custom_metrics, cols, descriptors):
        if scope is None:
            return None
        if scope == REPLICATION_METRICS or not self.version >= V9:
            log_func = self.log.debug
        else:
            log_func = self.log.warning

        results = None
        is_relations = scope.get('relation') and self._relations_manager.has_relations
        try:
            query = fmt.format(scope['query'], metrics_columns=", ".join(cols))
            with tracked_query(check=self, operation='custom_metrics' if is_custom_metrics else scope['name']):
                # if this is a relation-specific query, we need to list all relations last
                if is_relations:
                    schema_field = get_schema_field(descriptors)
                    formatted_query = self._relations_manager.filter_relation_query(query, schema_field)
                    cursor.execute(formatted_query)
                else:
                    self.log.debug("Running query: %s", str(query))
                    cursor.execute(query.replace(r'%', r'%%'))

                results = cursor.fetchall()
        except psycopg2.errors.FeatureNotSupported as e:
            # This happens for example when trying to get replication metrics from readers in Aurora. Let's ignore it.
            log_func(e)
            self.log.debug("Disabling replication metrics")
            self.is_aurora = False
            self.metrics_cache.replication_metrics = {}
        except psycopg2.errors.UndefinedFunction as e:
            log_func(e)
            log_func(
                "It seems the PG version has been incorrectly identified as %s. "
                "A reattempt to identify the right version will happen on next agent run." % self.version
            )
            self._clean_state()
        except (psycopg2.ProgrammingError, psycopg2.errors.QueryCanceled) as e:
            log_func("Not all metrics may be available: %s" % str(e))

        if not results:
            return None

        if is_custom_metrics and len(results) > MAX_CUSTOM_RESULTS:
            self.log.debug(
                "Query: %s returned more than %s results (%s). Truncating", query, MAX_CUSTOM_RESULTS, len(results)
            )
            results = results[:MAX_CUSTOM_RESULTS]

        if is_relations and len(results) > self._config.max_relations:
            self.log.debug(
                "Query: %s returned more than %s results (%s). "
                "Truncating. You can edit this limit by setting the `max_relations` config option",
                query,
                self._config.max_relations,
                len(results),
            )
            results = results[: self._config.max_relations]

        return results

    def _query_scope(self, cursor, scope, instance_tags, is_custom_metrics, dbname=None):
        if scope is None:
            return None
        # build query
        cols = list(scope['metrics'])  # list of metrics to query, in some order
        # we must remember that order to parse results

        # A descriptor is the association of a Postgres column name (e.g. 'schemaname')
        # to a tag name (e.g. 'schema').
        descriptors = scope['descriptors']
        results = self._run_query_scope(cursor, scope, is_custom_metrics, cols, descriptors)
        if not results:
            return None

        # Parse and submit results.

        num_results = 0

        for row in results:
            # A row contains descriptor values on the left (used for tagging), and
            # metric values on the right (used as values for metrics).
            # E.g.: (descriptor, descriptor, ..., value, value, value, value, ...)

            expected_number_of_columns = len(descriptors) + len(cols)
            if len(row) != expected_number_of_columns:
                raise RuntimeError(
                    'Row does not contain enough values: '
                    'expected {} ({} descriptors + {} columns), got {}'.format(
                        expected_number_of_columns, len(descriptors), len(cols), len(row)
                    )
                )

            descriptor_values = row[: len(descriptors)]
            column_values = row[len(descriptors) :]

            # build a map of descriptors and their values
            desc_map = {name: value for (_, name), value in zip(descriptors, descriptor_values)}

            # Build tags.

            # Add tags from the instance.
            # Special-case the "db" tag, which overrides the one that is passed as instance_tag
            # The reason is that pg_stat_database returns all databases regardless of the
            # connection.
            if not scope['relation'] and not scope.get('use_global_db_tag', False):
                tags = copy.copy(self.tags_without_db)
            elif dbname is not None:
                # if dbname is specified in this function, we are querying an autodiscovered database
                # and we need to tag it
                tags = copy.copy(self.tags_without_db)
                tags.append("db:{}".format(dbname))
            else:
                tags = copy.copy(instance_tags)

            # Add tags from descriptors.
            tags += [("%s:%s" % (k, v)) for (k, v) in iteritems(desc_map)]

            # Submit metrics to the Agent.
            for column, value in zip(cols, column_values):
                name, submit_metric = scope['metrics'][column]
                submit_metric(self, name, value, tags=set(tags), hostname=self.resolved_hostname)

                # if relation-level metrics idx_scan or seq_scan, cache it
                if name in ('postgresql.index_scans', 'postgresql.seq_scans'):
                    self._cache_table_activity(dbname, desc_map['table'], name, value)

            num_results += 1

        return num_results

    def _cache_table_activity(
        self,
        dbname: str,
        tablename: str,
        metric_name: str,
        value: int,
    ):
        db = dbname if self.autodiscovery else self._config.dbname
        if db not in self.metrics_cache.table_activity_metrics.keys():
            self.metrics_cache.table_activity_metrics[db] = {}
        if tablename not in self.metrics_cache.table_activity_metrics[db].keys():
            self.metrics_cache.table_activity_metrics[db][tablename] = {
                'postgresql.index_scans': 0,
                'postgresql.seq_scans': 0,
            }

        self.metrics_cache.table_activity_metrics[db][tablename][metric_name] = value

    def _collect_metric_autodiscovery(self, instance_tags, scopes, scope_type):
        if not self.autodiscovery:
            return

        start_time = time()
        databases = self.autodiscovery.get_items()
        for db in databases:
            with self.db_pool.get_connection(db, self._config.idle_connection_timeout) as conn:
                with conn.cursor(cursor_factory=CommenterCursor) as cursor:
                    for scope in scopes:
                        self._query_scope(cursor, scope, instance_tags, False, db)
        elapsed_ms = (time() - start_time) * 1000
        self.histogram(
            f"dd.postgres.{scope_type}.time",
            elapsed_ms,
            tags=self.tags + self._get_debug_tags(),
            hostname=self.resolved_hostname,
        )
        if elapsed_ms > self._config.min_collection_interval * 1000:
            self.record_warning(
                DatabaseConfigurationError.autodiscovered_metrics_exceeds_collection_interval,
                warning_with_tags(
                    "Collecting metrics on autodiscovery metrics took %d ms, which is longer than "
                    "the minimum collection interval. Consider increasing the min_collection_interval parameter "
                    "in the postgres yaml configuration.",
                    int(elapsed_ms),
                    code=DatabaseConfigurationError.autodiscovered_metrics_exceeds_collection_interval.value,
                    min_collection_interval=self._config.min_collection_interval,
                ),
            )

    def _collect_dynamic_queries_autodiscovery(self, queries):
        if not self.autodiscovery:
            return

        databases = self.autodiscovery.get_items()
        for dbname in databases:
            db = functools.partial(
                self.db_pool.get_connection, dbname=dbname, ttl_ms=self._config.idle_connection_timeout
            )
            self._dynamic_queries.append(self._new_query_executor(queries, db=db))

    def _emit_running_metric(self):
        self.gauge("postgresql.running", 1, tags=self.tags_without_db, hostname=self.resolved_hostname)

    def _collect_stats(self, instance_tags):
        """Query pg_stat_* for various metrics
        If relations is not an empty list, gather per-relation metrics
        on top of that.
        If custom_metrics is not an empty list, gather custom metrics defined in postgres.yaml
        """
        db_instance_metrics = self.metrics_cache.get_instance_metrics(self.version)
        bgw_instance_metrics = self.metrics_cache.get_bgw_metrics(self.version)
        archiver_instance_metrics = self.metrics_cache.get_archiver_metrics(self.version)

        metric_scope = [CONNECTION_METRICS]
        per_database_metric_scope = []

        if self._config.collect_function_metrics:
            # Function metrics are collected from all databases discovered
            per_database_metric_scope.append(FUNCTION_METRICS)
        if self._config.collect_count_metrics:
            # Count metrics are collected from all databases discovered
            per_database_metric_scope.append(COUNT_METRICS)
        if self.version >= V13:
            metric_scope.append(SLRU_METRICS)

        # Do we need relation-specific metrics?
        if self._config.relations:
            relations_scopes = list(RELATION_METRICS)

            if self._config.collect_bloat_metrics:
                relations_scopes.extend([INDEX_BLOAT, TABLE_BLOAT])

            # If autodiscovery is enabled, get relation metrics from all databases found
            if self.autodiscovery:
                self._collect_metric_autodiscovery(
                    instance_tags,
                    scopes=relations_scopes,
                    scope_type='_collect_relations_autodiscovery',
                )
            # otherwise, continue just with dbname
            else:
                metric_scope.extend(relations_scopes)

        replication_metrics = self.metrics_cache.get_replication_metrics(self.version, self.is_aurora)
        if replication_metrics:
            replication_metrics_query = copy.deepcopy(REPLICATION_METRICS)
            replication_metrics_query['metrics'] = replication_metrics
            metric_scope.append(replication_metrics_query)

        replication_stats_metrics = self.metrics_cache.get_replication_stats_metrics(self.version)
        if replication_stats_metrics:
            metric_scope.append(replication_stats_metrics)

        with self.db() as conn:
            with conn.cursor(cursor_factory=CommenterCursor) as cursor:
                results_len = self._query_scope(cursor, db_instance_metrics, instance_tags, False)
                if results_len is not None:
                    self.gauge(
                        "postgresql.db.count",
                        results_len,
                        tags=self.tags_without_db,
                        hostname=self.resolved_hostname,
                    )

            with conn.cursor(cursor_factory=CommenterCursor) as cursor:
                self._query_scope(cursor, bgw_instance_metrics, instance_tags, False)
            with conn.cursor(cursor_factory=CommenterCursor) as cursor:
                self._query_scope(cursor, archiver_instance_metrics, instance_tags, False)

            if self._config.collect_checksum_metrics and self.version >= V12:
                # SHOW queries need manual cursor execution so can't be bundled with the metrics
                with conn.cursor(cursor_factory=CommenterCursor) as cursor:
                    cursor.execute("SHOW data_checksums;")
                    enabled = cursor.fetchone()[0]
                    self.count(
                        "postgresql.checksums.enabled",
                        1,
                        tags=self.tags_without_db + ["enabled:" + "true" if enabled == "on" else "false"],
                        hostname=self.resolved_hostname,
                    )
            if self._config.collect_activity_metrics:
                activity_metrics = self.metrics_cache.get_activity_metrics(self.version)
                with conn.cursor(cursor_factory=CommenterCursor) as cursor:
                    self._query_scope(cursor, activity_metrics, instance_tags, False)

            if per_database_metric_scope:
                # if autodiscovery is enabled, get per-database metrics from all databases found
                if self.autodiscovery:
                    self._collect_metric_autodiscovery(
                        instance_tags,
                        scopes=per_database_metric_scope,
                        scope_type='_collect_stat_autodiscovery',
                    )
                else:
                    # otherwise, continue just with dbname
                    metric_scope.extend(per_database_metric_scope)

            for scope in list(metric_scope):
                with conn.cursor(cursor_factory=CommenterCursor) as cursor:
                    self._query_scope(cursor, scope, instance_tags, False)

            for scope in self._config.custom_metrics:
                with conn.cursor(cursor_factory=CommenterCursor) as cursor:
                    self._query_scope(cursor, scope, instance_tags, True)

        if self.dynamic_queries:
            for dynamic_query in self.dynamic_queries:
                dynamic_query.execute()

    def _new_connection(self, dbname):
        if self._config.host == 'localhost' and self._config.password == '':
            # Use ident method
            connection_string = "user=%s dbname=%s application_name=%s" % (
                self._config.user,
                dbname,
                self._config.application_name,
            )
            conn = psycopg2.connect(connection_string)
        else:
            password = self._config.password
            if 'aws' in self.cloud_metadata:
                # if we are running on AWS, check if IAM auth is enabled
                aws_managed_authentication = self.cloud_metadata['aws']['managed_authentication']
                if aws_managed_authentication['enabled']:
                    # if IAM auth is enabled, region must be set. Validation is done in the config
                    region = self.cloud_metadata['aws']['region']
                    password = aws.generate_rds_iam_token(
                        host=self._config.host,
                        username=self._config.user,
                        port=self._config.port,
                        region=region,
                    )
            elif 'azure' in self.cloud_metadata:
                azure_managed_authentication = self.cloud_metadata['azure']['managed_authentication']
                if azure_managed_authentication['enabled']:
                    client_id = azure_managed_authentication['client_id']
                    identity_scope = azure_managed_authentication.get('identity_scope', None)
                    password = azure.generate_managed_identity_token(client_id=client_id, identity_scope=identity_scope)

            args = {
                'host': self._config.host,
                'user': self._config.user,
                'password': password,
                'database': dbname,
                'sslmode': self._config.ssl_mode,
                'application_name': self._config.application_name,
            }
            if self._config.port:
                args['port'] = self._config.port
            if self._config.ssl_cert:
                args['sslcert'] = self._config.ssl_cert
            if self._config.ssl_root_cert:
                args['sslrootcert'] = self._config.ssl_root_cert
            if self._config.ssl_key:
                args['sslkey'] = self._config.ssl_key
            if self._config.ssl_password:
                args['sslpassword'] = self._config.ssl_password
            conn = psycopg2.connect(**args)
        # Autocommit is enabled by default for safety for all new connections (to prevent long-lived transactions).
        conn.set_session(autocommit=True, readonly=True)
        if self._config.query_timeout:
            # Set the statement_timeout for the session
            with conn.cursor() as cursor:
                cursor.execute("SET statement_timeout TO %d" % self._config.query_timeout)
        return conn

    def _connect(self):
        """
        Get and memoize connections to instances.
        The connection created here will be persistent. It will not be automatically
        evicted from the connection pool.
        """
        with self.db() as conn:
            self._connection_health_check(conn)

    # Reload pg_settings on a new connection to the main db
    def _load_pg_settings(self, db):
        try:
            with db.cursor(cursor_factory=CommenterDictCursor) as cursor:
                self.log.debug("Running query [%s]", PG_SETTINGS_QUERY)
                cursor.execute(
                    PG_SETTINGS_QUERY,
                    ("pg_stat_statements.max", "track_activity_query_size", "track_io_timing"),
                )
                rows = cursor.fetchall()
                self.pg_settings.clear()
                for setting in rows:
                    name, val = setting
                    self.pg_settings[name] = val
        except (psycopg2.DatabaseError, psycopg2.OperationalError) as err:
            self.log.warning("Failed to query for pg_settings: %s", repr(err))
            self.count(
                "dd.postgres.error",
                1,
                tags=self.tags + ["error:load-pg-settings"] + self._get_debug_tags(),
                hostname=self.resolved_hostname,
            )

    def _get_main_db(self):
        """
        Returns a memoized, persistent psycopg2 connection to `self.dbname`.
        Threadsafe as long as no transactions are used
        :return: a psycopg2 connection
        """
        # reload settings for the main DB only once every time the connection is reestablished
        return self.db_pool.get_connection(
            self._config.dbname,
            self._config.idle_connection_timeout,
            startup_fn=self._load_pg_settings,
            persistent=True,
        )

    def _close_db_pool(self):
        self.db_pool.close_all_connections()

    def _collect_custom_queries(self, tags):
        """
        Given a list of custom_queries, execute each query and parse the result for metrics
        """
        for custom_query in self._config.custom_queries:
            metric_prefix = custom_query.get('metric_prefix')
            if not metric_prefix:
                self.log.error("custom query field `metric_prefix` is required")
                continue
            metric_prefix = metric_prefix.rstrip('.')

            query = custom_query.get('query')
            if not query:
                self.log.error("custom query field `query` is required for metric_prefix `%s`", metric_prefix)
                continue

            columns = custom_query.get('columns')
            if not columns:
                self.log.error("custom query field `columns` is required for metric_prefix `%s`", metric_prefix)
                continue

            with self.db() as conn:
                with conn.cursor(cursor_factory=CommenterCursor) as cursor:
                    try:
                        self.log.debug("Running query: %s", query)
                        with tracked_query(
                            check=self, operation='custom_queries', tags=['metric_prefix:{}'.format(metric_prefix)]
                        ):
                            cursor.execute(query)
                    except (psycopg2.ProgrammingError, psycopg2.errors.QueryCanceled) as e:
                        self.log.error("Error executing query for metric_prefix %s: %s", metric_prefix, str(e))
                        continue

                    for row in cursor:
                        if not row:
                            self.log.debug("query result for metric_prefix %s: returned an empty result", metric_prefix)
                            continue

                        if len(columns) != len(row):
                            self.log.error(
                                "query result for metric_prefix %s: expected %s columns, got %s",
                                metric_prefix,
                                len(columns),
                                len(row),
                            )
                            continue

                        metric_info = []
                        query_tags = list(custom_query.get('tags', []))
                        query_tags.extend(tags)

                        for column, value in zip(columns, row):
                            # Columns can be ignored via configuration.
                            if not column:
                                continue

                            name = column.get('name')
                            if not name:
                                self.log.error("column field `name` is required for metric_prefix `%s`", metric_prefix)
                                break

                            column_type = column.get('type')
                            if not column_type:
                                self.log.error(
                                    "column field `type` is required for column `%s` of metric_prefix `%s`",
                                    name,
                                    metric_prefix,
                                )
                                break

                            if column_type == 'tag':
                                query_tags.append('{}:{}'.format(name, value))
                            else:
                                if not hasattr(self, column_type):
                                    self.log.error(
                                        "invalid submission method `%s` for column `%s` of metric_prefix `%s`",
                                        column_type,
                                        name,
                                        metric_prefix,
                                    )
                                    break
                                try:
                                    metric_info.append(('{}.{}'.format(metric_prefix, name), float(value), column_type))
                                except (ValueError, TypeError):
                                    self.log.error(
                                        "non-numeric value `%s` for metric column `%s` of metric_prefix `%s`",
                                        value,
                                        name,
                                        metric_prefix,
                                    )
                                    break

                        # Only submit metrics if there were absolutely no errors - all or nothing.
                        else:
                            for info in metric_info:
                                metric, value, method = info
                                getattr(self, method)(
                                    metric, value, tags=set(query_tags), hostname=self.resolved_hostname
                                )

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
        if self.resolved_hostname not in self._database_instance_emitted:
            event = {
                "host": self.resolved_hostname,
                "agent_version": datadog_agent.get_version(),
                "dbms": "postgres",
                "kind": "database_instance",
                "collection_interval": self._config.database_instance_collection_interval,
                'dbms_version': payload_pg_version(self.version),
                'integration_version': __version__,
                "tags": [t for t in self._non_internal_tags if not t.startswith('db:')],
                "timestamp": time() * 1000,
                "cloud_metadata": self.cloud_metadata,
                "metadata": {
                    "dbm": self._config.dbm_enabled,
                    "connection_host": self._config.host,
                },
            }
            self._database_instance_emitted[self.resolved_hostname] = event
            self.database_monitoring_metadata(json.dumps(event, default=default_json_event_encoding))

    def debug_stats_kwargs(self, tags=None):
        tags = self.tags + self._get_debug_tags() + (tags or [])
        return {
            'tags': tags,
            "hostname": self.resolved_hostname,
        }

    def check(self, _):
        tags = copy.copy(self.tags)
        self.tags_without_db = [t for t in copy.copy(self.tags) if not t.startswith("db:")]
        # Collect metrics
        try:
            # Check version
            self._connect()
            # We don't want to cache versions between runs to capture minor updates for metadata
            self.load_version()

            # Add raw version as a tag
            tags.append(f'postgresql_version:{self.raw_version}')
            self.tags_without_db.append(f'postgresql_version:{self.raw_version}')

            # Add system identifier as a tag
            self.load_system_identifier()
            tags.append(f'system_identifier:{self.system_identifier}')
            self.tags_without_db.append(f'system_identifier:{self.system_identifier}')

            if self._config.tag_replication_role:
                replication_role_tag = "replication_role:{}".format(self._get_replication_role())
                tags.append(replication_role_tag)
                self.tags_without_db.append(replication_role_tag)

            self.log.debug("Running check against version %s: is_aurora: %s", str(self.version), str(self.is_aurora))
            self._emit_running_metric()
            self._collect_stats(tags)
            self._collect_custom_queries(tags)
            if self._config.dbm_enabled:
                self.statement_metrics.run_job_loop(tags)
                self.statement_samples.run_job_loop(tags)
                self.metadata_samples.run_job_loop(tags)
            if self._config.collect_wal_metrics:
                # collect wal metrics for pg < 10, disabled by enabled
                self._collect_wal_metrics()
            self._send_database_instance_metadata()
        except Exception as e:
            self.log.exception("Unable to collect postgres metrics.")
            self._clean_state()
            message = u'Error establishing connection to postgres://{}:{}/{}, error is {}'.format(
                self._config.host, self._config.port, self._config.dbname, str(e)
            )
            self.service_check(
                self.SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                tags=tags,
                message=message,
                hostname=self.resolved_hostname,
            )
            raise e
        else:
            self.service_check(
                self.SERVICE_CHECK_NAME,
                AgentCheck.OK,
                tags=tags,
                hostname=self.resolved_hostname,
            )
        finally:
            # Add the warnings saved during the execution of the check
            self._report_warnings()
