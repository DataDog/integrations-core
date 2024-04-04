# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
# https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-PARAMKEYWORDS
import logging

from .util import (
    ACTIVITY_DD_METRICS,
    ACTIVITY_METRICS_8_3,
    ACTIVITY_METRICS_9_2,
    ACTIVITY_METRICS_9_6,
    ACTIVITY_METRICS_10,
    ACTIVITY_METRICS_LT_8_3,
    ACTIVITY_QUERY_10,
    ACTIVITY_QUERY_LT_10,
    CHECKSUM_METRICS,
    COMMON_ARCHIVER_METRICS,
    COMMON_BGW_METRICS,
    COMMON_METRICS,
    DATABASE_SIZE_METRICS,
    DBM_MIGRATED_METRICS,
    NEWER_14_METRICS,
    NEWER_91_BGW_METRICS,
    NEWER_92_BGW_METRICS,
    NEWER_92_METRICS,
    REPLICATION_METRICS_9_1,
    REPLICATION_METRICS_9_2,
    REPLICATION_METRICS_10,
    REPLICATION_STATS_METRICS,
)
from .version_utils import V8_3, V9, V9_1, V9_2, V9_4, V9_6, V10, V12, V14

logger = logging.getLogger(__name__)


class PostgresMetricsCache:
    """Maintains a cache of metrics to collect"""

    def __init__(self, config):
        self.config = config
        self.instance_metrics = None
        self.bgw_metrics = None
        self.archiver_metrics = None
        self.replication_metrics = None
        self.replication_stats_metrics = None
        self.activity_metrics = None
        self._count_metrics = None
        if self.config.relations:
            self.table_activity_metrics = {}

    def clean_state(self):
        self.instance_metrics = None
        self.bgw_metrics = None
        self.archiver_metrics = None
        self.replication_metrics = None
        self.replication_stats_metrics = None
        self.activity_metrics = None
        if self.config.relations:
            self.table_activity_metrics = {}

    def get_instance_metrics(self, version):
        """
        Add NEWER_92_METRICS to the default set of COMMON_METRICS when server
        version is 9.2 or later.

        Store the list of metrics in the check instance to avoid rebuilding it at
        every collection cycle.

        In case we have multiple instances pointing to the same postgres server
        monitoring different databases, we want to collect server metrics
        only once. See https://github.com/DataDog/dd-agent/issues/1211
        """
        metrics = self.instance_metrics
        if metrics is None:
            # if DBM enabled, do not collect postgresql.connections metric in the main check
            c_metrics = COMMON_METRICS
            if not self.config.dbm_enabled:
                c_metrics = dict(c_metrics, **DBM_MIGRATED_METRICS)
            # select the right set of metrics to collect depending on postgres version
            self.instance_metrics = dict(c_metrics)
            if version >= V9_2:
                self.instance_metrics = dict(self.instance_metrics, **NEWER_92_METRICS)
            if version >= V14:
                self.instance_metrics = dict(self.instance_metrics, **NEWER_14_METRICS)

            # add size metrics if needed
            if self.config.collect_database_size_metrics:
                self.instance_metrics.update(DATABASE_SIZE_METRICS)

            if self.config.collect_checksum_metrics and version >= V12:
                self.instance_metrics = dict(self.instance_metrics, **CHECKSUM_METRICS)

            metrics = self.instance_metrics

        res = {
            'descriptors': [('psd.datname', 'db')],
            'metrics': metrics,
            'query': "SELECT psd.datname, {metrics_columns} "
            "FROM pg_stat_database psd "
            "JOIN pg_database pd ON psd.datname = pd.datname",
            'relation': False,
            'name': 'instance_metrics',
        }

        res["query"] += " WHERE " + " AND ".join(
            "psd.datname not ilike '{}'".format(db) for db in self.config.ignore_databases
        )

        if self.config.dbstrict:
            res["query"] += " AND psd.datname in('{}')".format(self.config.dbname)

        return res

    def get_bgw_metrics(self, version):
        """Use either COMMON_BGW_METRICS or COMMON_BGW_METRICS + NEWER_92_BGW_METRICS
        depending on the postgres version.
        Uses a dictionary to save the result for each instance
        """
        # Extended 9.2+ metrics if needed
        if self.bgw_metrics is None:
            self.bgw_metrics = dict(COMMON_BGW_METRICS)

            if version >= V9_1:
                self.bgw_metrics.update(NEWER_91_BGW_METRICS)
            if version >= V9_2:
                self.bgw_metrics.update(NEWER_92_BGW_METRICS)

        if not self.bgw_metrics:
            return None

        return {
            'descriptors': [],
            'metrics': self.bgw_metrics,
            'query': "select {metrics_columns} FROM pg_stat_bgwriter",
            'relation': False,
            'name': 'bgw_metrics',
        }

    def get_archiver_metrics(self, version):
        """Use COMMON_ARCHIVER_METRICS to read from pg_stat_archiver as
        defined in 9.4 (first version to have this table).
        Uses a dictionary to save the result for each instance
        """
        # While there's only one set for now, prepare for future additions to
        # the table, mirroring get_bgw_metrics()
        if self.archiver_metrics is None and version >= V9_4:
            self.archiver_metrics = dict(COMMON_ARCHIVER_METRICS)

        if not self.archiver_metrics:
            return None

        return {
            'descriptors': [],
            'metrics': self.archiver_metrics,
            'query': "select {metrics_columns} FROM pg_stat_archiver",
            'relation': False,
            'name': 'archiver_metrics',
        }

    def get_replication_metrics(self, version, is_aurora):
        """Use either REPLICATION_METRICS_10, REPLICATION_METRICS_9_1, or
        REPLICATION_METRICS_9_1 + REPLICATION_METRICS_9_2, depending on the
        postgres version.
        Caches the result on a dictionary
        """
        if self.replication_metrics is not None:
            return self.replication_metrics

        if is_aurora:
            logger.debug("Detected Aurora %s. Won't collect replication metrics", version)
            self.replication_metrics = {}
        elif version >= V10:
            self.replication_metrics = dict(REPLICATION_METRICS_10)
        elif version >= V9_1:
            self.replication_metrics = dict(REPLICATION_METRICS_9_1)
            if version >= V9_2:
                self.replication_metrics.update(REPLICATION_METRICS_9_2)
        return self.replication_metrics

    def get_replication_stats_metrics(self, version):
        if version >= V10 and self.replication_stats_metrics is None:
            self.replication_stats_metrics = dict(REPLICATION_STATS_METRICS)
        return self.replication_stats_metrics

    def get_activity_metrics(self, version):
        """Use ACTIVITY_METRICS_LT_8_3 or ACTIVITY_METRICS_8_3 or ACTIVITY_METRICS_9_2
        depending on the postgres version in conjunction with ACTIVITY_QUERY_10 or ACTIVITY_QUERY_LT_10.
        Uses a dictionary to save the result for each instance
        """
        metrics_data = self.activity_metrics

        if metrics_data is None:
            excluded_aggregations = self.config.activity_metrics_excluded_aggregations
            if version < V9:
                excluded_aggregations.append('application_name')

            default_descriptors = [('application_name', 'app'), ('datname', 'db'), ('usename', 'user')]
            default_aggregations = [d[0] for d in default_descriptors]

            if 'datname' in excluded_aggregations:
                excluded_aggregations.remove('datname')
                logger.warning(
                    "datname is a required aggregation but was set in activity_metrics_excluded_aggregations. "
                    "Ignoring it and using the following instead: %s",
                    excluded_aggregations,
                )

            aggregation_columns = [a for a in default_aggregations if a not in excluded_aggregations]
            descriptors = [d for d in default_descriptors if d[0] not in excluded_aggregations]

            if version < V10:
                query = ACTIVITY_QUERY_LT_10
            else:
                query = ACTIVITY_QUERY_10
            if not aggregation_columns:
                query = query.format(aggregation_columns_select='', aggregation_columns_group='')
            else:
                query = query.format(
                    aggregation_columns_select=', '.join(aggregation_columns) + ',',
                    aggregation_columns_group=',' + ', '.join(aggregation_columns),
                )

            if version >= V10:
                metrics_query = ACTIVITY_METRICS_10
            elif version >= V9_6:
                metrics_query = ACTIVITY_METRICS_9_6
            elif version >= V9_2:
                metrics_query = ACTIVITY_METRICS_9_2
            elif version >= V8_3:
                metrics_query = ACTIVITY_METRICS_8_3
            else:
                metrics_query = ACTIVITY_METRICS_LT_8_3

            for i, q in enumerate(metrics_query):
                if '{dd__user}' in q:
                    metrics_query[i] = q.format(dd__user=self.config.user)

            metrics = dict(zip(metrics_query, ACTIVITY_DD_METRICS))

            self.activity_metrics = (metrics, query, descriptors)
        else:
            metrics, query, descriptors = metrics_data

        return {
            'descriptors': descriptors,
            'metrics': metrics,
            'query': query,
            'relation': False,
            'name': 'activity_metrics',
        }
