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
SELECT table_schema, table_name, rows_read, rows_changed
FROM information_schema.table_statistics"""

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

SQL_WORKER_THREADS = "SELECT THREAD_ID, NAME FROM performance_schema.threads WHERE NAME LIKE '%worker'"

SQL_PROCESS_LIST = "SELECT * FROM INFORMATION_SCHEMA.PROCESSLIST WHERE COMMAND LIKE '%Binlog dump%'"

SQL_INNODB_ENGINES = """\
SELECT engine
FROM information_schema.ENGINES
WHERE engine='InnoDB' and support != 'no' and support != 'disabled'"""

SQL_SERVER_ID_AWS_AURORA = """\
SHOW VARIABLES LIKE 'aurora_server_id'"""

SQL_REPLICATION_ROLE_AWS_AURORA = """\
SELECT IF(session_id = 'MASTER_SESSION_ID','writer', 'reader') AS replication_role
FROM information_schema.replica_host_status
WHERE server_id = @@aurora_server_id"""

SQL_GROUP_REPLICATION_MEMBER = """\
SELECT channel_name, member_state, member_role
FROM performance_schema.replication_group_members
WHERE member_id = @@server_uuid"""

SQL_GROUP_REPLICATION_METRICS = """\
SELECT channel_name,count_transactions_in_queue,count_transactions_checked,count_conflicts_detected,
count_transactions_rows_validating,count_transactions_remote_in_applier_queue,count_transactions_remote_applied,
count_transactions_local_proposed,count_transactions_local_rollback
FROM performance_schema.replication_group_member_stats
WHERE channel_name IN ('group_replication_applier', 'group_replication_recovery') AND member_id = @@server_uuid"""

SQL_GROUP_REPLICATION_PLUGIN_STATUS = """\
SELECT plugin_status
FROM information_schema.plugins WHERE plugin_name='group_replication'"""

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
