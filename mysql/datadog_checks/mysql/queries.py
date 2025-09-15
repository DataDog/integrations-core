# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

SQL_95TH_PERCENTILE = """SELECT `avg_us`, `ro` as `percentile` FROM
(SELECT `avg_us`, @rownum := @rownum + 1 as `ro` FROM
    (SELECT ROUND(avg_timer_wait / 1000000) as `avg_us`
        FROM performance_schema.events_statements_summary_by_digest
        ORDER BY `avg_us` ASC) p,
    (SELECT @rownum := 0) r) q
WHERE q.`ro` > ROUND(.95*@rownum)
ORDER BY `percentile` ASC
LIMIT 1"""

SQL_QUERY_TABLE_ROWS_STATS = """\
SELECT
    OBJECT_SCHEMA as table_schema,
    OBJECT_NAME as table_name,
    COUNT_READ as rows_read,
    COUNT_WRITE as rows_changed
FROM performance_schema.table_io_waits_summary_by_table
WHERE OBJECT_SCHEMA NOT IN ('mysql', 'performance_schema', 'information_schema')"""

SQL_QUERY_SCHEMA_SIZE = """\
SELECT table_schema, IFNULL(SUM(data_length+index_length)/1024/1024,0) AS total_mb
FROM information_schema.tables
GROUP BY table_schema"""

SQL_QUERY_TABLE_SIZE = """\
SELECT table_schema, table_name,
 IFNULL(index_length/1024/1024,0) AS index_size_mb,
 IFNULL(data_length/1024/1024,0) AS data_size_mb
FROM information_schema.tables
WHERE table_schema not in ('mysql', 'performance_schema', 'information_schema')"""

SQL_QUERY_SYSTEM_TABLE_SIZE = """\
SELECT table_schema, table_name,
 IFNULL(index_length/1024/1024,0) AS index_size_mb,
 IFNULL(data_length/1024/1024,0) AS data_size_mb
FROM information_schema.tables
WHERE table_schema in ('mysql', 'performance_schema', 'information_schema')"""

SQL_AVG_QUERY_RUN_TIME = """\
SELECT schema_name, ROUND((SUM(sum_timer_wait) / SUM(count_star)) / 1000000) AS avg_us
FROM performance_schema.events_statements_summary_by_digest
WHERE schema_name IS NOT NULL
GROUP BY schema_name"""

SQL_REPLICA_WORKER_THREADS = (
    "SELECT THREAD_ID, NAME FROM performance_schema.threads WHERE PROCESSLIST_COMMAND LIKE 'Binlog dump%'"
)

SQL_REPLICA_PROCESS_LIST = "SELECT * FROM INFORMATION_SCHEMA.PROCESSLIST WHERE COMMAND LIKE 'Binlog dump%'"

SQL_INNODB_ENGINES = """\
SELECT engine
FROM information_schema.ENGINES
WHERE engine='InnoDB' and support != 'no' and support != 'disabled'"""

SQL_REPLICATION_ROLE_AWS_AURORA = """\
SELECT IF(session_id = 'MASTER_SESSION_ID','writer', 'reader') AS replication_role
FROM information_schema.replica_host_status
WHERE server_id = @@aurora_server_id"""

SQL_GROUP_REPLICATION_MEMBER = """\
SELECT channel_name, member_state
FROM performance_schema.replication_group_members
WHERE member_id = @@server_uuid"""

SQL_GROUP_REPLICATION_MEMBER_8_0_2 = """\
SELECT channel_name, member_state, member_role
FROM performance_schema.replication_group_members
WHERE member_id = @@server_uuid"""

SQL_GROUP_REPLICATION_METRICS = """\
SELECT channel_name,count_transactions_in_queue,count_transactions_checked,count_conflicts_detected,
count_transactions_rows_validating
FROM performance_schema.replication_group_member_stats
WHERE channel_name IN ('group_replication_applier', 'group_replication_recovery') AND member_id = @@server_uuid"""

SQL_GROUP_REPLICATION_METRICS_8_0_2 = """\
SELECT channel_name,count_transactions_in_queue,count_transactions_checked,count_conflicts_detected,
count_transactions_rows_validating,count_transactions_remote_in_applier_queue,count_transactions_remote_applied,
count_transactions_local_proposed,count_transactions_local_rollback
FROM performance_schema.replication_group_member_stats
WHERE channel_name IN ('group_replication_applier', 'group_replication_recovery') AND member_id = @@server_uuid"""

SQL_GROUP_REPLICATION_PLUGIN_STATUS = """\
SELECT plugin_status
FROM information_schema.plugins WHERE plugin_name='group_replication'"""

# Alisases add to homogenize fields across different database types like SQLServer, PostgreSQL
SQL_DATABASES = """
SELECT schema_name as `name`,
       default_character_set_name as `default_character_set_name`,
       default_collation_name as `default_collation_name`
       FROM information_schema.SCHEMATA
       WHERE schema_name not in ('sys', 'mysql', 'performance_schema', 'information_schema')"""

SQL_TABLES = """\
SELECT table_name as `name`,
       engine as `engine`,
       row_format as `row_format`,
       create_time as `create_time`
       FROM information_schema.TABLES
       WHERE TABLE_SCHEMA = %s AND TABLE_TYPE="BASE TABLE"
"""

SQL_COLUMNS = """\
SELECT table_name as `table_name`,
       column_name as `name`,
       column_type as `column_type`,
       column_default as `default`,
       is_nullable as `nullable`,
       ordinal_position as `ordinal_position`,
       column_key as `column_key`,
       extra as `extra`
FROM INFORMATION_SCHEMA.COLUMNS
WHERE table_schema = %s AND table_name IN ({});
"""

SQL_INDEXES = """\
SELECT
    table_name as `table_name`,
    index_name as `name`,
    collation as `collation`,
    cardinality as `cardinality`,
    index_type as `index_type`,
    seq_in_index as `seq_in_index`,
    column_name as `column_name`,
    sub_part as `sub_part`,
    packed as `packed`,
    nullable as `nullable`,
    non_unique as `non_unique`,
    NULL as `expression`
FROM INFORMATION_SCHEMA.STATISTICS
WHERE table_schema = %s AND table_name IN ({});
"""

SQL_INDEXES_8_0_13 = """\
SELECT
    table_name as `table_name`,
    index_name as `name`,
    collation as `collation`,
    cardinality as `cardinality`,
    index_type as `index_type`,
    seq_in_index as `seq_in_index`,
    column_name as `column_name`,
    sub_part as `sub_part`,
    packed as `packed`,
    nullable as `nullable`,
    non_unique as `non_unique`,
    expression as `expression`
FROM INFORMATION_SCHEMA.STATISTICS
WHERE table_schema = %s AND table_name IN ({});
"""

SQL_FOREIGN_KEYS = """\
SELECT
    kcu.constraint_schema as constraint_schema,
    kcu.constraint_name as name,
    kcu.table_name as table_name,
    group_concat(kcu.column_name order by kcu.ordinal_position asc) as column_names,
    kcu.referenced_table_schema as referenced_table_schema,
    kcu.referenced_table_name as referenced_table_name,
    group_concat(kcu.referenced_column_name) as referenced_column_names,
    rc.update_rule as update_action,
    rc.delete_rule as delete_action
FROM
    INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
LEFT JOIN
    INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
    ON kcu.CONSTRAINT_SCHEMA = rc.CONSTRAINT_SCHEMA
    AND kcu.CONSTRAINT_NAME = rc.CONSTRAINT_NAME
WHERE
    kcu.table_schema = %s AND kcu.table_name in ({})
    AND kcu.referenced_table_name is not null
GROUP BY
    kcu.constraint_schema,
    kcu.constraint_name,
    kcu.table_name,
    kcu.referenced_table_schema,
    kcu.referenced_table_name,
    rc.update_rule,
    rc.delete_rule
"""

SQL_PARTITION = """\
SELECT
    table_name as `table_name`,
    partition_name as `name`,
    subpartition_name as `subpartition_name`,
    partition_ordinal_position as `partition_ordinal_position`,
    subpartition_ordinal_position as `subpartition_ordinal_position`,
    partition_method as `partition_method`,
    subpartition_method as `subpartition_method`,
    partition_expression as `partition_expression`,
    subpartition_expression as `subpartition_expression`,
    partition_description as `partition_description`,
    table_rows as `table_rows`,
    data_length as `data_length`
FROM INFORMATION_SCHEMA.PARTITIONS
WHERE
    table_schema = %s AND table_name in ({}) AND partition_name IS NOT NULL
"""

QUERY_DEADLOCKS = {
    'name': 'information_schema.INNODB_METRICS.lock_deadlocks',
    'query': """
        SELECT
            count as deadlocks
        FROM
            information_schema.INNODB_METRICS
        WHERE
            NAME='lock_deadlocks'
    """.strip(),
    'columns': [{'name': 'mysql.innodb.deadlocks', 'type': 'monotonic_count'}],
}

QUERY_USER_CONNECTIONS = {
    'name': 'performance_schema.threads',
    'query': """
        SELECT
            COUNT(processlist_user) AS connections,
            processlist_user,
            processlist_host,
            processlist_db,
            processlist_state
        FROM
            performance_schema.threads
        WHERE
            processlist_user IS NOT NULL AND
            processlist_state IS NOT NULL
        GROUP BY processlist_user, processlist_host, processlist_db, processlist_state
    """.strip(),
    'columns': [
        {'name': 'mysql.performance.user_connections', 'type': 'gauge'},
        {'name': 'processlist_user', 'type': 'tag'},
        {'name': 'processlist_host', 'type': 'tag'},
        {'name': 'processlist_db', 'type': 'tag'},
        {'name': 'processlist_state', 'type': 'tag'},
    ],
}


def show_replica_status_query(version, is_mariadb, channel=''):
    if version.version_compatible((10, 5, 1)) or not is_mariadb and version.version_compatible((8, 0, 22)):
        base_query = "SHOW REPLICA STATUS"
    else:
        base_query = "SHOW SLAVE STATUS"
    if channel and not is_mariadb:
        return "{0} FOR CHANNEL '{1}';".format(base_query, channel)
    else:
        return "{0};".format(base_query)


def get_indexes_query(version, is_mariadb, table_names):
    """
    Get the appropriate indexes query based on MySQL version and flavor.
    The EXPRESSION column was introduced in MySQL 8.0.13 for functional indexes.
    MariaDB doesn't support functional indexes.
    """
    if not is_mariadb and version.version_compatible((8, 0, 13)):
        return SQL_INDEXES_8_0_13.format(table_names)
    else:
        return SQL_INDEXES.format(table_names)
