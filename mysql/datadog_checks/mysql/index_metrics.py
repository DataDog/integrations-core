# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import is_affirmative

QUERY_INDEX_SIZE = {
    'name': 'mysql.innodb_index_stats',
    'query': """
        SELECT
            database_name,
            table_name,
            index_name,
            stat_value * @@innodb_page_size AS index_size_bytes
        FROM
            mysql.innodb_index_stats
        WHERE
            stat_name = 'size'
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
            object_schema,
            object_name,
            index_name,
            count_read,
            count_update,
            count_delete
        FROM
            performance_schema.table_io_waits_summary_by_index_usage
        WHERE index_name IS NOT NULL
        AND object_schema NOT IN ('mysql', 'performance_schema')
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
    def queries(self):
        # make a copy of the query to avoid modifying the original
        # in case different instances have different collection intervals
        usage_query = QUERY_INDEX_USAGE.copy()
        size_query = QUERY_INDEX_SIZE.copy()
        usage_query['collection_interval'] = self.collection_interval
        size_query['collection_interval'] = self.collection_interval
        return [size_query, usage_query]
