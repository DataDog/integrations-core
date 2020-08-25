# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base.utils.db import Query

# https://docs.snowflak e.com/en/sql-reference/account-usage/storage_usage.html
StorageUsageMetrics = Query(
    {
        'name': 'storage.metrics',
        'query': 'SELECT STORAGE_BYTES, STAGE_BYTES, FAILSAFE_BYTES from STORAGE_USAGE '
        'ORDER BY USAGE_DATE DESC LIMIT 1;',
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
        'query': "select SERVICE_TYPE, NAME, AVG(CREDITS_USED_COMPUTE), AVG(CREDITS_USED_CLOUD_SERVICES),"
        "AVG(CREDITS_USED) from METERING_HISTORY where convert_timezone('UTC', start_time) >= "
        "TIMESTAMP_FROM_PARTS(%s,%s,%s,%s,%s,%s) group by 1, 2;",
        'columns': [
            {'name': 'service_type', 'type': 'tag'},
            {'name': 'service', 'type': 'tag'},
            {'name': 'billing.virtual_warehouse', 'type': 'gauge'},
            {'name': 'billing.cloud_service', 'type': 'gauge'},
            {'name': 'billing.total', 'type': 'gauge'},
        ],
    }
)

# https://docs.snowflake.com/en/sql-reference/account-usage/warehouse_metering_history.html
WarehouseCreditUsage = Query(
    {
        'name': 'billings.warehouse.metrics',
        'query': "select WAREHOUSE_NAME, AVG(CREDITS_USED_COMPUTE), AVG(CREDITS_USED_CLOUD_SERVICES), AVG(CREDITS_USED)"
        " from WAREHOUSE_METERING_HISTORY where convert_timezone('UTC', start_time) >="
        " TIMESTAMP_FROM_PARTS(%s,%s,%s,%s,%s,%s) group by 1;",
        'columns': [
            {'name': 'warehouse', 'type': 'tag'},
            {'name': 'billing.warehouse.virtual_warehouse', 'type': 'gauge'},
            {'name': 'billing.warehouse.cloud_service', 'type': 'gauge'},
            {'name': 'billing.warehouse.total', 'type': 'gauge'},
        ],
    }
)

# https://docs.snowflake.com/en/sql-reference/account-usage/login_history.html
LoginMetrics = Query(
    {
        'name': 'login.metrics',
        'query': "select REPORTED_CLIENT_TYPE, sum(iff(IS_SUCCESS = 'NO', 1, 0)), sum(iff(IS_SUCCESS = 'YES', 1, 0)),"
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
        'query': 'select WAREHOUSE_NAME, AVG(AVG_RUNNING), AVG(AVG_QUEUED_LOAD), AVG(AVG_QUEUED_PROVISIONING),'
        ' AVG(AVG_BLOCKED) from WAREHOUSE_LOAD_HISTORY where convert_timezone("UTC", start_time) >='
        ' TIMESTAMP_FROM_PARTS(%s,%s,%s,%s,%s,%s);',
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
        'query': 'select QUERY_TYPE, WAREHOUSE_NAME, DATABASE_NAME, SCHEMA_NAME, AVG(EXECUTION_TIME), '
        'AVG(COMPILATION_TIME), AVG(BYTES_SCANNED), AVG(BYTES_WRITTEN), AVG(BYTES_DELETED) '
        'from QUERY_HISTORY where convert_timezone("UTC", start_time) >= TIMESTAMP_FROM_PARTS(%s,%s,%s,%s,%s,%s)'
        ' group by 1, 2, 3, 4;',
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
