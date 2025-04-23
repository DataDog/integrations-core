# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import is_affirmative

QUERY_INDEX_SIZE = {
    'name': 'mysql.innodb_index_stats',
    'query': """
        SELECT
            database_name,
            CASE
                WHEN table_name LIKE '%#p#%' THEN SUBSTRING_INDEX(table_name, '#p#', 1)
                ELSE table_name
            END AS base_table_name,
            index_name,
            SUM(stat_value * @@innodb_page_size) AS index_size_bytes
        FROM
            mysql.innodb_index_stats
        WHERE
            stat_name = 'size'
        GROUP BY
            database_name, base_table_name, index_name
        ORDER BY
            index_size_bytes DESC
        LIMIT {INDEX_LIMIT}
    """.strip(),
    'columns': [
        {'name': 'db', 'type': 'tag'},
        {'name': 'table', 'type': 'tag'},
        {'name': 'index', 'type': 'tag'},
        {'name': 'mysql.index.size', 'type': 'gauge'},
    ],
}
QUERY_INDEX_USAGE = {
    'name': 'performance_schema.table_io_waits_summary_by_index_usage',
    'query': """
        SELECT
            t.object_schema AS schema_name,
            t.object_name AS table_name,
            t.index_name,
            t.count_read,
            t.count_update,
            t.count_delete
        FROM performance_schema.table_io_waits_summary_by_index_usage t
        JOIN (
            SELECT
                database_name,
                CASE
                    WHEN table_name LIKE '%#p#%' THEN SUBSTRING_INDEX(table_name, '#p#', 1)
                    ELSE table_name
                END AS base_table_name,
                index_name,
                SUM(stat_value * @@innodb_page_size) AS index_size_bytes
            FROM
                mysql.innodb_index_stats
            WHERE
                stat_name = 'size'
            GROUP BY
                database_name, base_table_name, index_name
            ORDER BY
                index_size_bytes DESC
            LIMIT {INDEX_LIMIT}
        ) i ON t.object_schema = i.database_name
            AND t.object_name = i.base_table_name
            AND t.index_name = i.index_name
            AND t.index_name IS NOT NULL
    """.strip(),
    'columns': [
        {'name': 'db', 'type': 'tag'},
        {'name': 'table', 'type': 'tag'},
        {'name': 'index', 'type': 'tag'},
        {'name': 'mysql.index.reads', 'type': 'gauge'},
        {'name': 'mysql.index.updates', 'type': 'gauge'},
        {'name': 'mysql.index.deletes', 'type': 'gauge'},
    ],
}

DEFAULT_INDEX_METRIC_COLLECTION_INTERVAL = 300  # 5 minutes
DEFAULT_INDEX_LIMIT = 1000  # Default number of top indexes to collect


class MySqlIndexMetrics:
    def __init__(self, config):
        self._config = config

    @property
    def include_index_metrics(self) -> bool:
        return is_affirmative(self._config.index_config.get('enabled', True))

    @property
    def collection_interval(self) -> int:
        return int(self._config.index_config.get('collection_interval', DEFAULT_INDEX_METRIC_COLLECTION_INTERVAL))

    @property
    def index_limit(self) -> int:
        return int(self._config.index_config.get('limit', DEFAULT_INDEX_LIMIT))

    @property
    def queries(self):
        # make a copy of the query to avoid modifying the original
        # in case different instances have different collection intervals
        usage_query = QUERY_INDEX_USAGE.copy()
        size_query = QUERY_INDEX_SIZE.copy()

        # Update the index limit in the queries
        size_query['query'] = size_query['query'].format(INDEX_LIMIT=self.index_limit)
        usage_query['query'] = usage_query['query'].format(INDEX_LIMIT=self.index_limit)
        usage_query['collection_interval'] = self.collection_interval
        size_query['collection_interval'] = self.collection_interval
        return [size_query, usage_query]
