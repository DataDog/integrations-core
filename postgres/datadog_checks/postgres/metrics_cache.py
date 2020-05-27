# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
# https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-PARAMKEYWORDS
from .util import (
    ACTIVITY_DD_METRICS,
    ACTIVITY_METRICS_8_3,
    ACTIVITY_METRICS_9_2,
    ACTIVITY_METRICS_9_6,
    ACTIVITY_METRICS_LT_8_3,
    ACTIVITY_QUERY_10,
    ACTIVITY_QUERY_LT_10,
    COMMON_ARCHIVER_METRICS,
    COMMON_BGW_METRICS,
    COMMON_METRICS,
    COUNT_METRICS,
    DATABASE_SIZE_METRICS,
    NEWER_91_BGW_METRICS,
    NEWER_92_BGW_METRICS,
    NEWER_92_METRICS,
    REPLICATION_METRICS_9_1,
    REPLICATION_METRICS_9_2,
    REPLICATION_METRICS_10,
)
from .version_utils import V8_3, V9_1, V9_2, V9_4, V9_6, V10


class PostgresMetricsCache:
    """ Mantains a cache of metrics to collect """

    def __init__(self, config):
        self.config = config
        self.instance_metrics = None
        self.bgw_metrics = None
        self.archiver_metrics = None
        self.replication_metrics = None
        self.activity_metrics = None
        self._count_metrics = None

    def clean_state(self):
        self.instance_metrics = None
        self.bgw_metrics = None
        self.archiver_metrics = None
        self.replication_metrics = None
        self.activity_metrics = None

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
            # select the right set of metrics to collect depending on postgres version
            if version >= V9_2:
                self.instance_metrics = dict(COMMON_METRICS, **NEWER_92_METRICS)
            else:
                self.instance_metrics = dict(COMMON_METRICS)

            # add size metrics if needed
            if self.config.collect_database_size_metrics:
                self.instance_metrics.update(DATABASE_SIZE_METRICS)

            metrics = self.instance_metrics

        res = {
            'descriptors': [('psd.datname', 'db')],
            'metrics': metrics,
            'query': "SELECT psd.datname, {metrics_columns} "
            "FROM pg_stat_database psd "
            "JOIN pg_database pd ON psd.datname = pd.datname "
            "WHERE psd.datname not ilike 'template%%' "
            "  AND psd.datname not ilike 'rdsadmin' "
            "  AND psd.datname not ilike 'azure_maintenance' ",
            'relation': False,
        }

        if not self.config.collect_default_db:
            res["query"] += "  AND psd.datname not ilike 'postgres'"

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
        }

    def get_count_metrics(self):
        if self._count_metrics is not None:
            return self._count_metrics
        metrics = dict(COUNT_METRICS)
        metrics['query'] = COUNT_METRICS['query'].format(
            metrics_columns="{metrics_columns}", table_count_limit=self.config.table_count_limit
        )
        self._count_metrics = metrics
        return metrics

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
        }

    def get_replication_metrics(self, version):
        """ Use either REPLICATION_METRICS_10, REPLICATION_METRICS_9_1, or
        REPLICATION_METRICS_9_1 + REPLICATION_METRICS_9_2, depending on the
        postgres version.
        Uses a dictionnary to save the result for each instance
        """
        metrics = self.replication_metrics
        if version >= V10 and metrics is None:
            self.replication_metrics = dict(REPLICATION_METRICS_10)
            metrics = self.replication_metrics
        elif version >= V9_1 and metrics is None:
            self.replication_metrics = dict(REPLICATION_METRICS_9_1)
            if version >= V9_2:
                self.replication_metrics.update(REPLICATION_METRICS_9_2)
            metrics = self.replication_metrics
        return metrics

    def get_activity_metrics(self, version):
        """ Use ACTIVITY_METRICS_LT_8_3 or ACTIVITY_METRICS_8_3 or ACTIVITY_METRICS_9_2
        depending on the postgres version in conjunction with ACTIVITY_QUERY_10 or ACTIVITY_QUERY_LT_10.
        Uses a dictionnary to save the result for each instance
        """
        metrics_data = self.activity_metrics

        if metrics_data is None:
            query = ACTIVITY_QUERY_10 if version >= V10 else ACTIVITY_QUERY_LT_10
            if version >= V9_6:
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

            metrics = {k: v for k, v in zip(metrics_query, ACTIVITY_DD_METRICS)}
            self.activity_metrics = (metrics, query)
        else:
            metrics, query = metrics_data

        return {'descriptors': [('datname', 'db')], 'metrics': metrics, 'query': query, 'relation': False}
