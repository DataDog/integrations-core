# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from .const import OPTIMIZER_HINT_TEMPLATE

SQL_95TH_PERCENTILE = """SELECT {hint} `avg_us`, `ro` as `percentile` FROM
(SELECT `avg_us`, @rownum := @rownum + 1 as `ro` FROM
    (SELECT ROUND(avg_timer_wait / 1000000) as `avg_us`
        FROM performance_schema.events_statements_summary_by_digest
        ORDER BY `avg_us` ASC) p,
    (SELECT @rownum := 0) r) q
WHERE q.`ro` > ROUND(.95*@rownum)
ORDER BY `percentile` ASC
LIMIT 1""".format(hint=OPTIMIZER_HINT_TEMPLATE)

SQL_QUERY_SCHEMA_SIZE = """\
SELECT {hint} table_schema, IFNULL(SUM(data_length+index_length)/1024/1024,0) AS total_mb
FROM     information_schema.tables
GROUP BY table_schema""".format(hint=OPTIMIZER_HINT_TEMPLATE)

SQL_AVG_QUERY_RUN_TIME = """\
SELECT {hint} schema_name, ROUND((SUM(sum_timer_wait) / SUM(count_star)) / 1000000) AS avg_us
FROM performance_schema.events_statements_summary_by_digest
WHERE schema_name IS NOT NULL
GROUP BY schema_name""".format(hint=OPTIMIZER_HINT_TEMPLATE)

SQL_WORKER_THREADS = "SELECT {hint} THREAD_ID, NAME FROM performance_schema.threads WHERE NAME LIKE '%worker'".format(hint=OPTIMIZER_HINT_TEMPLATE)

SQL_PROCESS_LIST = "SELECT {hint} * FROM INFORMATION_SCHEMA.PROCESSLIST WHERE COMMAND LIKE '%Binlog dump%'".format(hint=OPTIMIZER_HINT_TEMPLATE)

SQL_INNODB_ENGINES = """\
SELECT {hint} engine
FROM information_schema.ENGINES
WHERE engine='InnoDB' and support != 'no' and support != 'disabled'""".format(hint=OPTIMIZER_HINT_TEMPLATE)

SQL_SERVER_ID_AWS_AURORA = """\
SHOW VARIABLES LIKE 'aurora_server_id'"""

SQL_REPLICATION_ROLE_AWS_AURORA = """\
SELECT {hint} IF(session_id = 'MASTER_SESSION_ID','writer', 'reader') AS replication_role
FROM information_schema.replica_host_status
WHERE server_id = @@aurora_server_id""".format(hint=OPTIMIZER_HINT_TEMPLATE)


def show_replica_status_query(version, is_mariadb, channel=''):
    if version.version_compatible((10, 5, 1)) or not is_mariadb and version.version_compatible((8, 0, 22)):
        base_query = "SHOW REPLICA STATUS"
    else:
        base_query = "SHOW SLAVE STATUS"
    if channel and not is_mariadb:
        return "{0} FOR CHANNEL '{1}';".format(base_query, channel)
    else:
        return "{0};".format(base_query)
