# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base.utils.db import Query

# https://docs.snowflak e.com/en/sql-reference/account-usage/storage_usage.html
StorageUsageMetrics = Query(
    {
        'name': 'storage.metrics',
        'query': 'SELECT STORAGE_BYTES, STAGE_BYTES, FAILSAFE_BYTES from STORAGE_USAGE'
        ' ORDER BY USAGE_DATE DESC LIMIT 1;',
        'columns': [
            {'name': 'storage.storage_bytes.total', 'type': 'gauge'},
            {'name': 'storage.stage_bytes.total', 'type': 'gauge'},
            {'name': 'storage.failsafe_bytes.total', 'type': 'gauge'},
        ],
    }
)

# https://docs.snowflake.com/en/sql-reference/account-usage/database_storage_usage_history.html
DatabaseStorageMetrics = Query(
    {
        'name': 'database_storage.metrics',
        'query': 'SELECT DATABASE_NAME, AVERAGE_DATABASE_BYTES, '
        'AVERAGE_FAILSAFE_BYTES from DATABASE_STORAGE_USAGE_HISTORY ORDER BY USAGE_DATE DESC LIMIT 1;',
        'columns': [
            {'name': 'database', 'type': 'tag'},
            {'name': 'storage.database.storage_bytes', 'type': 'gauge'},
            {'name': 'storage.database.failsafe_bytes', 'type': 'gauge'},
        ],
    }
)

# https://docs.snowflake.com/en/sql-reference/account-usage/metering_history.html
CreditUsage = Query(
    {
        'name': 'billing.metrics',
        'query': "select SERVICE_TYPE, NAME, sum(CREDITS_USED_COMPUTE), avg(CREDITS_USED_COMPUTE), "
        "sum(CREDITS_USED_CLOUD_SERVICES), avg(CREDITS_USED_CLOUD_SERVICES), "
        "sum(CREDITS_USED), avg(CREDITS_USED) from METERING_HISTORY"
        " where start_time >= date_trunc(day, current_date) group by 1, 2;",
        'columns': [
            {'name': 'service_type', 'type': 'tag'},
            {'name': 'service', 'type': 'tag'},
            {'name': 'billing.virtual_warehouse.sum', 'type': 'gauge'},
            {'name': 'billing.virtual_warehouse.avg', 'type': 'gauge'},
            {'name': 'billing.cloud_service.sum', 'type': 'gauge'},
            {'name': 'billing.cloud_service.avg', 'type': 'gauge'},
            {'name': 'billing.total_credit.sum', 'type': 'gauge'},
            {'name': 'billing.total_credit.avg', 'type': 'gauge'},
        ],
    }
)

# https://docs.snowflake.com/en/sql-reference/account-usage/warehouse_metering_history.html
WarehouseCreditUsage = Query(
    {
        'name': 'billings.warehouse.metrics',
        'query': "select WAREHOUSE_NAME, sum(CREDITS_USED_COMPUTE), avg(CREDITS_USED_COMPUTE), "
        "sum(CREDITS_USED_CLOUD_SERVICES), avg(CREDITS_USED_CLOUD_SERVICES), "
        "sum(CREDITS_USED), avg(CREDITS_USED) from WAREHOUSE_METERING_HISTORY "
        "where start_time >= date_trunc(day, current_date) group by 1;",
        'columns': [
            {'name': 'warehouse', 'type': 'tag'},
            {'name': 'billing.warehouse.virtual_warehouse.sum', 'type': 'gauge'},
            {'name': 'billing.warehouse.virtual_warehouse.avg', 'type': 'gauge'},
            {'name': 'billing.warehouse.cloud_service.sum', 'type': 'gauge'},
            {'name': 'billing.warehouse.cloud_service.avg', 'type': 'gauge'},
            {'name': 'billing.warehouse.total_credit.sum', 'type': 'gauge'},
            {'name': 'billing.warehouse.total_credit.avg', 'type': 'gauge'},
        ],
    }
)

# https://docs.snowflake.com/en/sql-reference/account-usage/login_history.html
LoginMetrics = Query(
    {
        'name': 'login.metrics',
        'query': "select REPORTED_CLIENT_TYPE, sum(iff(IS_SUCCESS = 'NO', 1, 0)), sum(iff(IS_SUCCESS = 'YES', 1, 0)), "
        "count(*) from LOGIN_HISTORY group by REPORTED_CLIENT_TYPE;",
        'columns': [
            {'name': 'client_type', 'type': 'tag'},
            {'name': 'logins.fail.count', 'type': 'monotonic_count'},
            {'name': 'logins.success.count', 'type': 'monotonic_count'},
            {'name': 'logins.total', 'type': 'monotonic_count'},
        ],
    }
)

# https://docs.snowflake.com/en/sql-reference/account-usage/warehouse_load_history.html
WarehouseLoad = Query(
    {
        'name': 'warehouse_load.metrics',
        'query': "select WAREHOUSE_NAME, AVG(AVG_RUNNING), AVG(AVG_QUEUED_LOAD), AVG(AVG_QUEUED_PROVISIONING), "
        "AVG(AVG_BLOCKED) from WAREHOUSE_LOAD_HISTORY "
        "where start_time >= date_trunc(day, current_date) group by 1;",
        'columns': [
            {'name': 'warehouse', 'type': 'tag'},
            {'name': 'query.executed', 'type': 'gauge'},
            {'name': 'query.queued_overload', 'type': 'gauge'},
            {'name': 'query.queued_provision', 'type': 'gauge'},
            {'name': 'query.blocked', 'type': 'gauge'},
        ],
    }
)

# https://docs.snowflake.com/en/sql-reference/account-usage/query_history.html
QueryHistory = Query(
    {
        'name': 'warehouse_load.metrics',
        'query': "select QUERY_TYPE, WAREHOUSE_NAME, DATABASE_NAME, SCHEMA_NAME, AVG(EXECUTION_TIME), "
        "AVG(COMPILATION_TIME), AVG(BYTES_SCANNED), AVG(BYTES_WRITTEN), AVG(BYTES_DELETED) "
        "from QUERY_HISTORY where start_time >= date_trunc(day, current_date)"
        " group by 1, 2, 3, 4;",
        'columns': [
            {'name': 'query_type', 'type': 'tag'},
            {'name': 'warehouse', 'type': 'tag'},
            {'name': 'database', 'type': 'tag'},
            {'name': 'schema', 'type': 'tag'},
            {'name': 'query.execution_time', 'type': 'gauge'},
            {'name': 'query.compilation_time', 'type': 'gauge'},
            {'name': 'query.bytes_scanned', 'type': 'gauge'},
            {'name': 'query.bytes_written', 'type': 'gauge'},
            {'name': 'query.bytes_deleted', 'type': 'gauge'},
        ],
    }
)

# https://docs.snowflake.com/en/sql-reference/account-usage/data_transfer_history.html
DataTransferHistory = Query(
    {
        'name': 'data_transfer.metrics',
        'query': 'select source_cloud, source_region, target_cloud, target_region, transfer_type, '
        'avg(bytes_transferred), sum(bytes_transferred) from DATA_TRANSFER_HISTORY '
        'where start_time >= date_trunc(day, current_date) group by 1, 2, 3, 4, 5;',
        'columns': [
            {'name': 'source_cloud', 'type': 'tag'},
            {'name': 'source_region', 'type': 'tag'},
            {'name': 'target_cloud', 'type': 'tag'},
            {'name': 'target_region', 'type': 'tag'},
            {'name': 'transfer_type', 'type': 'tag'},
            {'name': 'data_transfer.bytes.avg', 'type': 'gauge'},
            {'name': 'data_transfer.bytes.sum', 'type': 'gauge'},
        ],
    }
)

# https://docs.snowflake.com/en/sql-reference/account-usage/automatic_clustering_history.html
AutoReclusterHistory = Query(
    {
        'name': 'auto_recluster.metrics',
        'query': 'select table_name, database_name, schema_name, avg(credits_used), sum(credits_used), '
        'avg(num_bytes_reclustered), sum(num_bytes_reclustered), '
        'avg(num_rows_reclustered), sum(num_rows_reclustered) '
        'from automatic_clustering_history where start_time >= date_trunc(day, current_date) group by 1, 2, 3;',
        'columns': [
            {'name': 'table', 'type': 'tag'},
            {'name': 'database', 'type': 'tag'},
            {'name': 'schema', 'type': 'tag'},
            {'name': 'auto_recluster.credits_used.avg', 'type': 'gauge'},
            {'name': 'auto_recluster.credits_used.sum', 'type': 'gauge'},
            {'name': 'auto_recluster.bytes_reclustered.avg', 'type': 'gauge'},
            {'name': 'auto_recluster.bytes_reclustered.sum', 'type': 'gauge'},
            {'name': 'auto_recluster.rows_reclustered.avg', 'type': 'gauge'},
            {'name': 'auto_recluster.rows_reclustered.sum', 'type': 'gauge'},
        ],
    }
)
