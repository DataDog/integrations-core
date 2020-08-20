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
        'query': "select SERVICE_TYPE, NAME, CREDITS_USED_COMPUTE, CREDITS_USED_CLOUD_SERVICES, CREDITS_USED from"
        " METERING_HISTORY where start_time >= TIMESTAMP_FROM_PARTS(%s,%s,%s,%s,%s,%s);",
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
        'query': "select WAREHOUSE_NAME, CREDITS_USED_COMPUTE, CREDITS_USED_CLOUD_SERVICES, "
        "CREDITS_USED from WAREHOUSE_METERING_HISTORY where start_time >= TIMESTAMP_FROM_PARTS(%s,%s,%s,%s,%s,%s);",
        'columns': [
            {'name': 'warehouse', 'type': 'tag'},
            {'name': 'billing.warehouse.virtual_warehouse', 'type': 'gauge'},
            {'name': 'billing.warehouse.cloud_service', 'type': 'gauge'},
            {'name': 'billing.warehouse.total', 'type': 'gauge'},
        ],
    }
)
