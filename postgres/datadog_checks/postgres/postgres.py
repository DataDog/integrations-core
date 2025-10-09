# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import contextlib
import copy
import functools
import os
from string import Template
from time import time

import psycopg
from cachetools import TTLCache

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.db import QueryExecutor
from datadog_checks.base.utils.db.core import QueryManager
from datadog_checks.base.utils.db.health import HealthEvent, HealthStatus
from datadog_checks.base.utils.db.utils import (
    default_json_event_encoding,
    tracked_query,
)
from datadog_checks.base.utils.db.utils import resolve_db_host as agent_host_resolver
from datadog_checks.base.utils.serialization import json
from datadog_checks.postgres.connection_pool import (
    AWSTokenProvider,
    AzureTokenProvider,
    LRUConnectionPoolManager,
    PostgresConnectionArgs,
    TokenAwareConnection,
    TokenProvider,
)
from datadog_checks.postgres.discovery import PostgresAutodiscovery
from datadog_checks.postgres.health import PostgresHealth
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
from .config import build_config, sanitize
from .util import (
    ANALYZE_PROGRESS_METRICS,
    AWS_RDS_HOSTNAME_SUFFIX,
    AZURE_DEPLOYMENT_TYPE_TO_RESOURCE_TYPE,
    BUFFERCACHE_METRICS,
    CLUSTER_VACUUM_PROGRESS_METRICS,
    CONNECTION_METRICS,
    COUNT_METRICS,
    FUNCTION_METRICS,
    IDLE_TX_LOCK_AGE_METRICS,
    INDEX_PROGRESS_METRICS,
    QUERY_PG_CONTROL_CHECKPOINT,
    QUERY_PG_CONTROL_CHECKPOINT_LT_10,
    QUERY_PG_REPLICATION_SLOTS,
    QUERY_PG_REPLICATION_SLOTS_STATS,
    QUERY_PG_REPLICATION_STATS_METRICS,
    QUERY_PG_STAT_DATABASE,
    QUERY_PG_STAT_DATABASE_CONFLICTS,
    QUERY_PG_STAT_RECOVERY_PREFETCH,
    QUERY_PG_STAT_WAL_RECEIVER,
    QUERY_PG_UPTIME,
    QUERY_PG_WAIT_EVENT_METRICS,
    REPLICATION_METRICS,
    SLRU_METRICS,
    SNAPSHOT_TXID_METRICS,
    SNAPSHOT_TXID_METRICS_LT_13,
    STAT_IO_METRICS,
    STAT_SUBSCRIPTION_METRICS,
    STAT_SUBSCRIPTION_STATS_METRICS,
    STAT_WAL_METRICS,
    SUBSCRIPTION_STATE_METRICS,
    VACUUM_PROGRESS_METRICS,
    VACUUM_PROGRESS_METRICS_LT_17,
    WAL_FILE_METRICS,
    DatabaseConfigurationError,
    DatabaseHealthCheckError,  # noqa: F401
    fmt,
    get_schema_field,
    payload_pg_version,
    warning_with_tags,
)
from .version_utils import V9, V9_2, V10, V12, V13, V14, V15, V16, V17, VersionUtils

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

MAX_CUSTOM_RESULTS = 100

PG_SETTINGS_QUERY = "SELECT name, setting FROM pg_settings WHERE name IN (%s, %s, %s)"


class PostgreSql(AgentCheck):
    """Collects per-database, and optionally per-relation metrics, custom metrics"""

    __NAMESPACE__ = 'postgresql'

    SOURCE_TYPE_NAME = 'postgresql'
    SERVICE_CHECK_NAME = 'postgres.can_connect'
    METADATA_TRANSFORMERS = {'version': VersionUtils.transform_version}

    HA_SUPPORTED = True

    def __init__(self, name, init_config, instances):
        super(PostgreSql, self).__init__(name, init_config, instances)
        self.health = PostgresHealth(self)
        self._resolved_hostname = None
        self._database_identifier = None
        self._agent_hostname = None
        self._database_hostname = None
        self._db = None
        self._cloud_metadata: dict[str, dict] = None
        self.version = None
        self.raw_version = None
        self.system_identifier = None
        self.cluster_name = None
        self.is_aurora = None
        self.wal_level = None
        self._version_utils = VersionUtils()

        config, validation_result = build_config(self)
        self._config = config
        # Log validation errors and warnings
        for error in validation_result.errors:
            self.log.error(error)
        for warning in validation_result.warnings:
            self.log.warning(warning)

        self.tags = list(self._config.tags)
        self.add_core_tags()

        try:
            # Handle the config validation result after we've set tags so those tags are included in the health event
            self.health.submit_health_event(
                name=HealthEvent.INITIALIZATION,
                status=HealthStatus.ERROR
                if not validation_result.valid
                else HealthStatus.WARNING
                if validation_result.warnings
                else HealthStatus.OK,
                errors=[str(error) for error in validation_result.errors],
                warnings=validation_result.warnings,
                config=sanitize(self._config),
                instance=sanitize(self.instance),
                features=validation_result.features,
            )
        except Exception as e:
            self.log.error("Error submitting health event for initialization: %s", e)

        # Abort initializing the check if the config is invalid
        if validation_result.valid is False:
            self.log.error("Configuration validation failed: %s", validation_result.errors)
            raise validation_result.errors[0]

        # Keep a copy of the tags without the internal resource tags so they can be used for paths that don't
        # go through the agent internal metrics submission processing those tags
        self._non_internal_tags = copy.deepcopy(self.tags)
        self.set_resource_tags()
        self.pg_settings = {}
        self._warnings_by_code = {}
        self.db_pool = LRUConnectionPoolManager(
            max_db=self._config.max_connections,
            base_conn_args=self.build_connection_args(),
            statement_timeout=self._config.query_timeout,
            sqlascii_encodings=self._config.query_encodings,
            token_provider=self.build_token_provider(),
        )
        self.metrics_cache = PostgresMetricsCache(self._config)
        self.statement_metrics = PostgresStatementMetrics(self, self._config)
        self.statement_samples = PostgresStatementSamples(self, self._config)
        self.metadata_samples = PostgresMetadata(self, self._config)
        self._relations_manager = RelationsManager(self._config.relations, self._config.max_relations)
        self._clean_state()
        self._query_manager = QueryManager(self, lambda _: None, queries=[])  # query executor is set later
        self.check_initializations.append(
            lambda: RelationsManager.validate_relations_config(list(self._config.relations))
        )
        self.check_initializations.append(self.set_resolved_hostname_metadata)
        self.check_initializations.append(self._connect)
        self.check_initializations.append(self.load_cluster_name)
        self.check_initializations.append(self.load_version)
        self.check_initializations.append(self.load_system_identifier)
        self.check_initializations.append(self.initialize_is_aurora)
        self.check_initializations.append(self._query_manager.compile_queries)
        self.tags_without_db = [t for t in copy.copy(self.tags) if not t.startswith("db:")]
        self.autodiscovery = self._build_autodiscovery()
        self._dynamic_queries = []
        # _database_instance_emitted: limit the collection and transmission of the database instance metadata
        self._database_instance_emitted = TTLCache(
            maxsize=1,
            ttl=self._config.database_instance_collection_interval,
        )  # type: TTLCache

    def _build_autodiscovery(self):
        if not self._config.database_autodiscovery.enabled:
            return None

        if not self._config.relations:
            self.log.warning(
                "Database autodiscovery is enabled, but relation-level metrics are not being collected."
                "All metrics will be gathered from global view."
            )

        discovery = PostgresAutodiscovery(
            self,
            self._config.database_autodiscovery.global_view_db,
            self._config.database_autodiscovery,
            self._config.idle_connection_timeout,
        )
        return discovery

    def add_core_tags(self):
        """
        Add tags that should be attached to every metric/event but which require check calculations outside the config.
        """
        self.tags.append("database_hostname:{}".format(self.database_hostname))
        self.tags.append("database_instance:{}".format(self.database_identifier))

    def set_resource_tags(self):
        if self._config.gcp.project_id and self._config.gcp.instance_id:
            self.tags.append(
                "dd.internal.resource:gcp_sql_database_instance:{}:{}".format(
                    self._config.gcp.project_id, self._config.gcp.instance_id
                )
            )
        if self._config.aws.instance_endpoint:
            self.tags.append(
                "dd.internal.resource:aws_rds_instance:{}".format(
                    self._config.aws.instance_endpoint,
                )
            )
        elif AWS_RDS_HOSTNAME_SUFFIX in self.resolved_hostname:
            # allow for detecting if the host is an RDS host, and emit
            # the resource properly even if the `aws` config is unset
            self.tags.append("dd.internal.resource:aws_rds_instance:{}".format(self.resolved_hostname))
        if self._config.azure.deployment_type and self._config.azure.fully_qualified_domain_name:
            deployment_type = self._config.azure.deployment_type
            # some `deployment_type`s map to multiple `resource_type`s
            resource_type = AZURE_DEPLOYMENT_TYPE_TO_RESOURCE_TYPE.get(deployment_type)
            if resource_type:
                self.tags.append(
                    "dd.internal.resource:{}:{}".format(resource_type, self._config.azure.fully_qualified_domain_name)
                )
        # finally, tag the `database_instance` resource for this instance
        # metrics intake will use this tag to add all the tags for the instance
        self.tags.append(
            "dd.internal.resource:database_instance:{}".format(
                self.database_identifier,
            )
        )

    def _new_query_executor(self, queries, db):
        return QueryExecutor(
            functools.partial(self.execute_query_raw, db=db),
            self,
            queries=queries,
            tags=self.tags_without_db,
            hostname=self.reported_hostname,
            track_operation_time=True,
        )

    def execute_query_raw(self, query, db):
        with db() as conn:
            with conn.cursor() as cursor:
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
        if self._db.info.status != psycopg.pq.ConnStatus.OK:
            self._db.rollback()
        try:
            yield self._db
        except (psycopg.InterfaceError, InterruptedError):
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
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchall()
                self.log.debug("Connection health check passed for database %s", conn.info.dbname)
        except psycopg.Error as e:
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
                ]
            )

        if self.is_aurora and self.wal_level != 'logical':
            self.log.debug("logical wal_level is required to use pg_current_wal_lsn() on Aurora")

        else:
            self.log.debug("Adding control checkpoint metrics")

            if self.version >= V10:
                queries.append(QUERY_PG_CONTROL_CHECKPOINT)

            else:
                queries.append(QUERY_PG_CONTROL_CHECKPOINT_LT_10)

        if self.version >= V10:
            # Wal receiver is not supported on aurora
            # select * from pg_stat_wal_receiver;
            # ERROR:  Function pg_stat_get_wal_receiver() is currently not supported in Aurora
            if self.is_aurora is False:
                queries.append(QUERY_PG_STAT_WAL_RECEIVER)
                if self._config.collect_wal_metrics is not False:
                    # collect wal metrics for pg >= 10 only if the user has not explicitly disabled it
                    queries.append(WAL_FILE_METRICS)
            if self._config.collect_buffercache_metrics:
                queries.append(BUFFERCACHE_METRICS)
            queries.append(QUERY_PG_REPLICATION_SLOTS)
            queries.append(QUERY_PG_REPLICATION_STATS_METRICS)
            queries.append(VACUUM_PROGRESS_METRICS if self.version >= V17 else VACUUM_PROGRESS_METRICS_LT_17)
            queries.append(STAT_SUBSCRIPTION_METRICS)
            queries.append(QUERY_PG_WAIT_EVENT_METRICS)

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
            queries.append(QUERY_PG_STAT_RECOVERY_PREFETCH)
        if self.version >= V16:
            if self._config.dbm:
                queries.append(STAT_IO_METRICS)

        if self._config.dbm and self._config.locks_idle_in_transaction.enabled:
            query_def = copy.deepcopy(IDLE_TX_LOCK_AGE_METRICS)
            query_def['collection_interval'] = self._config.locks_idle_in_transaction.collection_interval
            max_rows = self._config.locks_idle_in_transaction.max_rows
            query_def['query'] = query_def['query'].format(max_rows=max_rows)
            per_database_queries.append(query_def)

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
        if self._config.dbm:
            self.statement_samples.cancel()
            self.statement_metrics.cancel()
            self.metadata_samples.cancel()
            if self.statement_metrics._job_loop_future:
                self.statement_metrics._job_loop_future.result()
            if self.statement_samples._job_loop_future:
                self.statement_samples._job_loop_future.result()
            if self.metadata_samples._job_loop_future:
                self.metadata_samples._job_loop_future.result()
        self._close_db_pool()

    def _clean_state(self):
        self.log.debug("Cleaning state")
        self.metrics_cache.clean_state()
        self._dynamic_queries = []

    def _get_debug_tags(self):
        return ['agent_hostname:{}'.format(self.agent_hostname)]

    def _get_replication_role(self):
        with self.db() as conn:
            with conn.cursor() as cursor:
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
                "wal_age",
                wal_file_age,
                tags=self.tags_without_db,
                hostname=self.reported_hostname,
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
            with conn.cursor() as cursor:
                cursor.execute('SELECT system_identifier FROM pg_control_system();')
                self.system_identifier = cursor.fetchone()[0]

    def load_cluster_name(self):
        with self.db() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SHOW cluster_name;')
                self.cluster_name = cursor.fetchone()[0]

    def load_version(self):
        self.raw_version = self._version_utils.get_raw_version(self.db())
        self.version = self._version_utils.parse_version(self.raw_version)
        self.set_metadata('version', self.raw_version)

    def initialize_is_aurora(self):
        if self.is_aurora is None:
            self.is_aurora = self._version_utils.is_aurora(self.db())
        return self.is_aurora

    def _get_wal_level(self):
        with self.db() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SHOW wal_level;')
                wal_level = cursor.fetchone()[0]
                return wal_level

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
    def database_identifier(self):
        # type: () -> str
        if self._database_identifier is None:
            template = Template(self._config.database_identifier.template)
            tag_dict = {}
            tags = self.tags.copy()
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
            self._database_identifier = template.safe_substitute(**tag_dict)
        return self._database_identifier

    @property
    def cloud_metadata(self):
        if self._cloud_metadata is None:
            self._cloud_metadata = {
                "aws": self._config.aws.model_dump(),
                "azure": self._config.azure.model_dump(),
                "gcp": self._config.gcp.model_dump(),
            }
        return self._cloud_metadata

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

    @property
    def database_hostname(self):
        # type: () -> str
        if self._database_hostname is None:
            self._database_hostname = self.resolve_db_host()
        return self._database_hostname

    def resolve_db_host(self):
        return agent_host_resolver(self._config.host)

    def _run_query_scope(self, scope, is_custom_metrics, cols, descriptors, dbname=None):
        if scope is None:
            return None
        if scope == REPLICATION_METRICS or not self.version >= V9:
            log_func = self.log.debug
        else:
            log_func = self.log.warning

        results = None
        is_relations = scope.get('relation') and self._relations_manager.has_relations
        try:
            with self.db() if dbname is None else self.db_pool.get_connection(dbname) as conn:
                with conn.cursor() as cursor:
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
                        if not results:
                            return None

                        if is_custom_metrics and len(results) > MAX_CUSTOM_RESULTS:
                            self.log.debug(
                                "Query: %s returned more than %s results (%s). Truncating",
                                query,
                                MAX_CUSTOM_RESULTS,
                                len(results),
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

        except psycopg.errors.FeatureNotSupported as e:
            # This happens for example when trying to get replication metrics from readers in Aurora. Let's ignore it.
            log_func(e)
            self.log.debug("Disabling replication metrics")
            self.is_aurora = False
            self.metrics_cache.replication_metrics = {}
        except psycopg.errors.UndefinedFunction as e:
            log_func(e)
            log_func(
                "It seems the PG version has been incorrectly identified as %s. "
                "A reattempt to identify the right version will happen on next agent run." % self.version
            )
            self._clean_state()
        except (psycopg.ProgrammingError, psycopg.errors.QueryCanceled) as e:
            log_func("Not all metrics may be available: %s" % str(e))
        except psycopg.Error as e:
            log_func(
                "Error while executing query: %s. ",
                e,
            )

            return None

    def _query_scope(self, scope, instance_tags, is_custom_metrics, dbname=None):
        if scope is None:
            return None
        # build query
        cols = list(scope['metrics'])  # list of metrics to query, in some order
        # we must remember that order to parse results

        # A descriptor is the association of a Postgres column name (e.g. 'schemaname')
        # to a tag name (e.g. 'schema').
        descriptors = scope['descriptors']
        results = self._run_query_scope(scope, is_custom_metrics, cols, descriptors, dbname=dbname)
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
                    'Row does not contain enough values: expected {} ({} descriptors + {} columns), got {}'.format(
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
            tags += [("%s:%s" % (k, v)) for (k, v) in desc_map.items()]

            # Submit metrics to the Agent.
            for column, value in zip(cols, column_values):
                name, submit_metric = scope['metrics'][column]
                submit_metric(self, name, value, tags=set(tags), hostname=self.reported_hostname)

                # if relation-level metrics idx_scan or seq_scan, cache it
                if name in ('index_scans', 'seq_scans'):
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
                'index_scans': 0,
                'seq_scans': 0,
            }

        self.metrics_cache.table_activity_metrics[db][tablename][metric_name] = value

    def _collect_metric_autodiscovery(self, instance_tags, scopes, scope_type):
        if not self.autodiscovery:
            return

        start_time = time()
        databases = self.autodiscovery.get_items()
        for db in databases:
            try:
                for scope in scopes:
                    self._query_scope(scope, instance_tags, False, dbname=db)
            except Exception as e:
                self.log.error("Error collecting metrics for database %s %s", db, str(e))
        elapsed_ms = (time() - start_time) * 1000
        self.histogram(
            f"dd.postgres.{scope_type}.time",
            elapsed_ms,
            tags=self.tags + self._get_debug_tags(),
            hostname=self.reported_hostname,
            raw=True,
        )
        telemetry_metric = scope_type.replace("_", "", 1)  # remove the first underscore to match telemetry convention
        datadog_agent.emit_agent_telemetry("postgres", f"{telemetry_metric}_ms", elapsed_ms, "histogram")
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
            db = functools.partial(self.db_pool.get_connection, dbname=dbname)
            self._dynamic_queries.append(self._new_query_executor(queries, db=db))

    def _emit_running_metric(self):
        self.gauge("running", 1, tags=self.tags_without_db, hostname=self.reported_hostname)

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

        results_len = self._query_scope(db_instance_metrics, instance_tags, False)
        if results_len is not None:
            self.gauge(
                "db.count",
                results_len,
                tags=self.tags_without_db,
                hostname=self.reported_hostname,
            )

        self._query_scope(bgw_instance_metrics, instance_tags, False)
        self._query_scope(archiver_instance_metrics, instance_tags, False)

        if self._config.collect_checksum_metrics and self.version >= V12:
            # SHOW queries need manual cursor execution so can't be bundled with the metrics
            with self.db() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SHOW data_checksums;")
                    enabled = cursor.fetchone()[0]
                    self.count(
                        "checksums.enabled",
                        1,
                        tags=self.tags_without_db + ["enabled:" + "true" if enabled == "on" else "false"],
                        hostname=self.reported_hostname,
                    )
        if self._config.collect_activity_metrics:
            activity_metrics = self.metrics_cache.get_activity_metrics(self.version)
            self._query_scope(activity_metrics, instance_tags, False)

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
            self._query_scope(scope, instance_tags, False)

        for scope in self._config.custom_metrics:
            self._query_scope(scope, instance_tags, True)

        if self.dynamic_queries:
            for dynamic_query in self.dynamic_queries:
                dynamic_query.execute()

    def build_token_provider(self) -> TokenProvider:
        if self._config.aws.managed_authentication.enabled:
            return AWSTokenProvider(
                host=self._config.host,
                port=self._config.port,
                username=self._config.username,
                region=self._config.aws.region,
                role_arn=self._config.aws.managed_authentication.role_arn,
            )
        elif self._config.azure.managed_authentication.enabled:
            return AzureTokenProvider(
                client_id=self._config.azure.managed_authentication.client_id,
                identity_scope=self._config.azure.managed_authentication.identity_scope,
            )
        else:
            return None

    def build_connection_args(self) -> PostgresConnectionArgs:
        if self._config.host == 'localhost' and self._config.password == '':
            return PostgresConnectionArgs(
                application_name=self._config.application_name,
                username=self._config.username,
            )
        else:
            return PostgresConnectionArgs(
                application_name=self._config.application_name,
                username=self._config.username,
                host=self._config.host,
                port=self._config.port,
                password=self._config.password,
                ssl_mode=self._config.ssl,
                ssl_cert=self._config.ssl_cert,
                ssl_root_cert=self._config.ssl_root_cert,
                ssl_key=self._config.ssl_key,
                ssl_password=self._config.ssl_password,
            )

    def _new_connection(self, dbname):
        # TODO: Keeping this main connection outside of the pool for now to keep existing behavior.
        # We should move this to the pool in the future.
        conn_args = self.build_connection_args()
        kwargs = conn_args.as_kwargs(dbname=dbname)

        # Pass the token_provider as a kwarg so it's available to TokenAwareConnection.connect()
        if self.db_pool.token_provider:
            kwargs["token_provider"] = self.db_pool.token_provider

        conn = TokenAwareConnection.connect(**kwargs)
        self.db_pool._configure_connection(conn)
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
            with db.cursor() as cursor:
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
        except psycopg.Error as err:
            self.log.warning("Failed to query for pg_settings: %s", repr(err))
            self.count(
                "dd.postgres.error",
                1,
                tags=self.tags + ["error:load-pg-settings"] + self._get_debug_tags(),
                hostname=self.reported_hostname,
                raw=True,
            )

    def _get_main_db(self):
        """
        Returns a memoized, persistent psycopg connection to `self.dbname`.
        Threadsafe as long as no transactions are used
        :return: a psycopg connection
        """
        # reload settings for the main DB only once every time the connection is reestablished
        conn = self.db_pool.get_connection(
            self._config.dbname,
            persistent=True,
        )

        return conn

    def _close_db_pool(self):
        self.db_pool.close_all()

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
                "dbms": "postgres",
                "kind": "database_instance",
                "collection_interval": self._config.database_instance_collection_interval,
                'dbms_version': payload_pg_version(self.version),
                'integration_version': __version__,
                "tags": [t for t in self._non_internal_tags if not t.startswith('db:')],
                "timestamp": time() * 1000,
                "cloud_metadata": self.cloud_metadata,
                "metadata": {
                    "dbm": self._config.dbm,
                    "connection_host": self._config.host,
                },
            }
            self._database_instance_emitted[self.database_identifier] = event
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
        tags_to_add = []
        try:
            # Check version
            self._connect()
            # We don't want to cache versions between runs to capture minor updates for metadata
            self.load_version()

            # Check wal_level
            self.wal_level = self._get_wal_level()

            # Add raw version as a tag
            tags.append(f'postgresql_version:{self.raw_version}')
            tags_to_add.append(f'postgresql_version:{self.raw_version}')

            # Add system identifier as a tag
            if self.system_identifier:
                tags.append(f'system_identifier:{self.system_identifier}')
                tags_to_add.append(f'system_identifier:{self.system_identifier}')

            # Add cluster name if it was set
            if self.cluster_name:
                tags.append(f'postgresql_cluster_name:{self.cluster_name}')
                tags_to_add.append(f'postgresql_cluster_name:{self.cluster_name}')

            if self._config.tag_replication_role:
                replication_role_tag = "replication_role:{}".format(self._get_replication_role())
                tags.append(replication_role_tag)
                tags_to_add.append(replication_role_tag)
            self._update_tag_sets(tags_to_add)
            self._send_database_instance_metadata()

            self.log.debug("Running check against version %s: is_aurora: %s", str(self.version), str(self.is_aurora))
            self._emit_running_metric()
            self._collect_stats(tags)
            if self._query_manager.queries:
                self._query_manager.executor = functools.partial(self.execute_query_raw, db=self.db)
                self._query_manager.execute(extra_tags=tags)
            if self._config.dbm:
                self.statement_metrics.run_job_loop(tags)
                self.statement_samples.run_job_loop(tags)
                self.metadata_samples.run_job_loop(tags)
            if self._config.collect_wal_metrics:
                # collect wal metrics for pg < 10, disabled by enabled
                self._collect_wal_metrics()
        except Exception as e:
            self.log.exception("Unable to collect postgres metrics.")
            self._clean_state()
            message = 'Error establishing connection to postgres://{}:{}/{}, error is {}'.format(
                self._config.host, self._config.port, self._config.dbname, str(e)
            )
            self.service_check(
                self.SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                tags=tags,
                message=message,
                hostname=self.reported_hostname,
                raw=True,
            )
            raise e
        else:
            self.service_check(
                self.SERVICE_CHECK_NAME,
                AgentCheck.OK,
                tags=tags,
                hostname=self.reported_hostname,
                raw=True,
            )
        finally:
            # Add the warnings saved during the execution of the check
            self._report_warnings()

    def _update_tag_sets(self, tags):
        self._non_internal_tags = list(set(self._non_internal_tags) | set(tags))
        self.tags_without_db = list(set(self.tags_without_db) | set(tags))
