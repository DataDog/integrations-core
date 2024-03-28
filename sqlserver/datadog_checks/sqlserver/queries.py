# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


INDEX_USAGE_STATS_QUERY = {
    "name": "sys.dm_db_index_usage_stats",
    "query": """
    SELECT
         DB_NAME(ixus.database_id) as db,
         CASE
            WHEN ind.name IS NULL THEN 'HeapIndex_' + OBJECT_NAME(ind.object_id)
            ELSE ind.name
         END AS index_name,
         OBJECT_NAME(ind.object_id) as table_name,
        user_seeks,
        user_scans,
        user_lookups,
        user_updates
    FROM sys.indexes ind
             INNER JOIN sys.dm_db_index_usage_stats ixus
             ON ixus.index_id = ind.index_id AND ixus.object_id = ind.object_id
    WHERE OBJECTPROPERTY(ind.object_id, 'IsUserTable') = 1 AND DB_NAME(ixus.database_id) = db_name()
    GROUP BY ixus.database_id, OBJECT_NAME(ind.object_id), ind.name, user_seeks, user_scans, user_lookups, user_updates
""",
    "columns": [
        {"name": "db", "type": "tag"},
        {"name": "index_name", "type": "tag"},
        {"name": "table", "type": "tag"},
        {"name": "index.user_seeks", "type": "monotonic_count"},
        {"name": "index.user_scans", "type": "monotonic_count"},
        {"name": "index.user_lookups", "type": "monotonic_count"},
        {"name": "index.user_updates", "type": "monotonic_count"},
    ],
}
