# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# https://docs.snowflake.com/en/sql-reference/account-usage/storage_usage.html
StorageUsageMetrics = {
    'name': 'storage.metrics',
    'query': ('SELECT STORAGE_BYTES, STAGE_BYTES, FAILSAFE_BYTES from STORAGE_USAGE ORDER BY USAGE_DATE DESC LIMIT 1;'),
    'columns': [
        {'name': 'storage.storage_bytes.total', 'type': 'gauge'},
        {'name': 'storage.stage_bytes.total', 'type': 'gauge'},
        {'name': 'storage.failsafe_bytes.total', 'type': 'gauge'},
    ],
}

# https://docs.snowflake.com/en/sql-reference/account-usage/database_storage_usage_history.html
DatabaseStorageMetrics = {
    'name': 'database_storage.metrics',
    'query': (
        'SELECT DATABASE_NAME, AVERAGE_DATABASE_BYTES, AVERAGE_FAILSAFE_BYTES '
        'from DATABASE_STORAGE_USAGE_HISTORY ORDER BY USAGE_DATE DESC LIMIT 1;'
    ),
    'columns': [
        {'name': 'database', 'type': 'tag'},
        {'name': 'storage.database.storage_bytes', 'type': 'gauge'},
        {'name': 'storage.database.failsafe_bytes', 'type': 'gauge'},
    ],
}


# https://docs.snowflake.com/en/sql-reference/account-usage/metering_history.html
CreditUsage = {
    'name': 'billing.metrics',
    'query': (
        'select SERVICE_TYPE, NAME, sum(CREDITS_USED_COMPUTE), avg(CREDITS_USED_COMPUTE), '
        'sum(CREDITS_USED_CLOUD_SERVICES), avg(CREDITS_USED_CLOUD_SERVICES), '
        'sum(CREDITS_USED), avg(CREDITS_USED) from METERING_HISTORY '
        'where start_time >= DATEADD(hour, -24, current_timestamp()) group by 1, 2;'
    ),
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


# https://docs.snowflake.com/en/sql-reference/account-usage/warehouse_metering_history.html
WarehouseCreditUsage = {
    'name': 'billing.warehouse.metrics',
    'query': (
        'select WAREHOUSE_NAME, sum(CREDITS_USED_COMPUTE), avg(CREDITS_USED_COMPUTE), '
        'sum(CREDITS_USED_CLOUD_SERVICES), avg(CREDITS_USED_CLOUD_SERVICES), '
        'sum(CREDITS_USED), avg(CREDITS_USED) from WAREHOUSE_METERING_HISTORY '
        'where start_time >= DATEADD(hour, -24, current_timestamp()) group by 1;'
    ),
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


# https://docs.snowflake.com/en/sql-reference/account-usage/login_history.html
LoginMetrics = {
    'name': 'login.metrics',
    'query': (
        "select REPORTED_CLIENT_TYPE, sum(iff(IS_SUCCESS = 'NO', 1, 0)), sum(iff(IS_SUCCESS = 'YES', 1, 0)), "
        "count(*) from LOGIN_HISTORY group by REPORTED_CLIENT_TYPE;"
    ),
    'columns': [
        {'name': 'client_type', 'type': 'tag'},
        {'name': 'logins.fail.count', 'type': 'monotonic_count'},
        {'name': 'logins.success.count', 'type': 'monotonic_count'},
        {'name': 'logins.total', 'type': 'monotonic_count'},
    ],
}

# https://docs.snowflake.com/en/sql-reference/account-usage/warehouse_load_history.html
WarehouseLoad = {
    'name': 'warehouse_load.metrics',
    'query': (
        'select WAREHOUSE_NAME, AVG(AVG_RUNNING), AVG(AVG_QUEUED_LOAD), AVG(AVG_QUEUED_PROVISIONING), '
        'AVG(AVG_BLOCKED) from WAREHOUSE_LOAD_HISTORY '
        'where start_time >= DATEADD(hour, -24, current_timestamp()) group by 1;'
    ),
    'columns': [
        {'name': 'warehouse', 'type': 'tag'},
        {'name': 'query.executed', 'type': 'gauge'},
        {'name': 'query.queued_overload', 'type': 'gauge'},
        {'name': 'query.queued_provision', 'type': 'gauge'},
        {'name': 'query.blocked', 'type': 'gauge'},
    ],
}

# https://docs.snowflake.com/en/sql-reference/account-usage/query_history.html
QueryHistory = {
    'name': 'warehouse_load.metrics',
    'query': (
        'select QUERY_TYPE, WAREHOUSE_NAME, DATABASE_NAME, SCHEMA_NAME, AVG(EXECUTION_TIME), '
        'AVG(COMPILATION_TIME), AVG(BYTES_SCANNED), AVG(BYTES_WRITTEN), AVG(BYTES_DELETED), '
        'AVG(BYTES_SPILLED_TO_LOCAL_STORAGE), AVG(BYTES_SPILLED_TO_REMOTE_STORAGE) '
        'from QUERY_HISTORY where start_time >= DATEADD(hour, -24, current_timestamp()) '
        'group by 1, 2, 3, 4;'
    ),
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
        {'name': 'query.bytes_spilled.local', 'type': 'gauge'},
        {'name': 'query.bytes_spilled.remote', 'type': 'gauge'},
    ],
}

# https://docs.snowflake.com/en/sql-reference/account-usage/data_transfer_history.html
DataTransferHistory = {
    'name': 'data_transfer.metrics',
    'query': (
        'select source_cloud, source_region, target_cloud, target_region, transfer_type, '
        'avg(bytes_transferred), sum(bytes_transferred) from DATA_TRANSFER_HISTORY '
        'where start_time >= DATEADD(hour, -24, current_timestamp()) group by 1, 2, 3, 4, 5;'
    ),
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

# https://docs.snowflake.com/en/sql-reference/account-usage/automatic_clustering_history.html
AutoReclusterHistory = {
    'name': 'auto_recluster.metrics',
    'query': (
        'select table_name, database_name, schema_name, avg(credits_used), sum(credits_used), '
        'avg(num_bytes_reclustered), sum(num_bytes_reclustered), '
        'avg(num_rows_reclustered), sum(num_rows_reclustered) '
        'from automatic_clustering_history where start_time >= DATEADD(hour, -24, current_timestamp()) '
        'group by 1, 2, 3;'
    ),
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

# https://docs.snowflake.com/en/sql-reference/account-usage/table_storage_metrics.html
TableStorage = {
    'name': 'table_storage.metrics',
    'query': (
        'select table_name, table_schema, avg(ACTIVE_BYTES), avg(TIME_TRAVEL_BYTES), avg(FAILSAFE_BYTES), '
        'avg(RETAINED_FOR_CLONE_BYTES) from table_storage_metrics group by 1, 2'
    ),
    'columns': [
        {'name': 'table', 'type': 'tag'},
        {'name': 'schema', 'type': 'tag'},
        {'name': 'storage.table.active_bytes.avg', 'type': 'gauge'},
        {'name': 'storage.table.time_travel_bytes.avg', 'type': 'gauge'},
        {'name': 'storage.table.failsafe_bytes.avg', 'type': 'gauge'},
        {'name': 'storage.table.retained_bytes.avg', 'type': 'gauge'},
    ],
}

# https://docs.snowflake.com/en/sql-reference/account-usage/pipe_usage_history.html
PipeHistory = {
    'name': 'pipe.metrics',
    'query': (
        'select history.pipe_name, p.pipe_schema, p.pipe_catalog, '
        'avg(credits_used), sum(credits_used), avg(bytes_inserted), sum(bytes_inserted), '
        'avg(files_inserted), sum(files_inserted) from pipe_usage_history as history '
        'join pipes p on p.pipe_id = history.pipe_id '
        'where start_time >= DATEADD(hour, -24, current_timestamp()) group by 1,2,3;'
    ),
    'columns': [
        {'name': 'pipe', 'type': 'tag'},
        {'name': 'schema', 'type': 'tag'},
        {'name': 'database', 'type': 'tag'},
        {'name': 'pipe.credits_used.avg', 'type': 'gauge'},
        {'name': 'pipe.credits_used.sum', 'type': 'gauge'},
        {'name': 'pipe.bytes_inserted.avg', 'type': 'gauge'},
        {'name': 'pipe.bytes_inserted.sum', 'type': 'gauge'},
        {'name': 'pipe.files_inserted.avg', 'type': 'gauge'},
        {'name': 'pipe.files_inserted.sum', 'type': 'gauge'},
    ],
}

# https://docs.snowflake.com/en/sql-reference/account-usage/replication_usage_history.html
ReplicationUsage = {
    'name': 'replication.metrics',
    'query': (
        'select database_name, avg(credits_used), sum(credits_used), '
        'avg(bytes_transferred), sum(bytes_transferred) from replication_usage_history '
        'where start_time >= DATEADD(hour, -24, current_timestamp()) group by 1;'
    ),
    'columns': [
        {'name': 'database', 'type': 'tag'},
        {'name': 'replication.credits_used.avg', 'type': 'gauge'},
        {'name': 'replication.credits_used.sum', 'type': 'gauge'},
        {'name': 'replication.bytes_transferred.avg', 'type': 'gauge'},
        {'name': 'replication.bytes_transferred.sum', 'type': 'gauge'},
    ],
}


# https://docs.snowflake.com/en/sql-reference/organization-usage/contract_items.html
OrgContractItems = {
    'name': 'organization.contract.metrics',
    'query': ('select CONTRACT_NUMBER, CONTRACT_ITEM, CURRENCY, sum(AMOUNT) from CONTRACT_ITEMS group by 1, 2, 3;'),
    'columns': [
        {'name': 'contract_number', 'type': 'tag'},
        {'name': 'contract_item', 'type': 'tag'},
        {'name': 'currency', 'type': 'tag'},
        {'name': 'organization.contract.amount', 'type': 'gauge'},
    ],
}

# https://docs.snowflake.com/en/sql-reference/organization-usage/metering_daily_history.html
OrgCreditUsage = {
    'name': 'organization.credit.metrics',
    'query': (
        'select ACCOUNT_NAME, SERVICE_TYPE, '
        'sum(CREDITS_USED_COMPUTE), avg(CREDITS_USED_COMPUTE), '
        'sum(CREDITS_USED_CLOUD_SERVICES), avg(CREDITS_USED_CLOUD_SERVICES), '
        'sum(CREDITS_ADJUSTMENT_CLOUD_SERVICES), avg(CREDITS_ADJUSTMENT_CLOUD_SERVICES), '
        'sum(CREDITS_USED), avg(CREDITS_USED), sum(CREDITS_BILLED), avg(CREDITS_BILLED) from METERING_DAILY_HISTORY '
        'where USAGE_DATE = DATEADD(day, -1, current_date) group by 1, 2;'
    ),
    'columns': [
        {'name': 'billing_account', 'type': 'tag'},
        {'name': 'service_type', 'type': 'tag'},
        {'name': 'organization.credit.virtual_warehouse.sum', 'type': 'gauge'},
        {'name': 'organization.credit.virtual_warehouse.avg', 'type': 'gauge'},
        {'name': 'organization.credit.cloud_service.sum', 'type': 'gauge'},
        {'name': 'organization.credit.cloud_service.avg', 'type': 'gauge'},
        {'name': 'organization.credit.cloud_service_adjustment.sum', 'type': 'gauge'},
        {'name': 'organization.credit.cloud_service_adjustment.avg', 'type': 'gauge'},
        {'name': 'organization.credit.total_credit.sum', 'type': 'gauge'},
        {'name': 'organization.credit.total_credit.avg', 'type': 'gauge'},
        {'name': 'organization.credit.total_credits_billed.sum', 'type': 'gauge'},
        {'name': 'organization.credit.total_credits_billed.avg', 'type': 'gauge'},
    ],
}

# https://docs.snowflake.com/en/sql-reference/organization-usage/usage_in_currency_daily.html
OrgCurrencyUsage = {
    'name': 'organization.currency.metrics',
    'query': (
        'select ACCOUNT_NAME, SERVICE_LEVEL, USAGE_TYPE, CURRENCY, '
        'sum(USAGE), sum(USAGE_IN_CURRENCY) from USAGE_IN_CURRENCY_DAILY '
        'where USAGE_DATE = DATEADD(day, -1, current_date) group by 1, 2, 3, 4;'
    ),
    'columns': [
        {'name': 'billing_account', 'type': 'tag'},
        {'name': 'service_level', 'type': 'tag'},
        {'name': 'usage_type', 'type': 'tag'},
        {'name': 'currency', 'type': 'tag'},
        {'name': 'organization.currency.usage', 'type': 'gauge'},
        {'name': 'organization.currency.usage_in_currency', 'type': 'gauge'},
    ],
}


# https://docs.snowflake.com/en/sql-reference/organization-usage/warehouse_metering_history.html
OrgWarehouseCreditUsage = {
    'name': 'organization.warehouse.metrics',
    'query': (
        'select WAREHOUSE_NAME, ACCOUNT_NAME, sum(CREDITS_USED_COMPUTE), avg(CREDITS_USED_COMPUTE), '
        'sum(CREDITS_USED_CLOUD_SERVICES), avg(CREDITS_USED_CLOUD_SERVICES), '
        'sum(CREDITS_USED), avg(CREDITS_USED) from WAREHOUSE_METERING_HISTORY '
        'where start_time = DATEADD(day, -1, current_date) group by 1, 2;'
    ),
    'columns': [
        {'name': 'warehouse', 'type': 'tag'},
        {'name': 'billing_account', 'type': 'tag'},
        {'name': 'organization.warehouse.virtual_warehouse.sum', 'type': 'gauge'},
        {'name': 'organization.warehouse.virtual_warehouse.avg', 'type': 'gauge'},
        {'name': 'organization.warehouse.cloud_service.sum', 'type': 'gauge'},
        {'name': 'organization.warehouse.cloud_service.avg', 'type': 'gauge'},
        {'name': 'organization.warehouse.total_credit.sum', 'type': 'gauge'},
        {'name': 'organization.warehouse.total_credit.avg', 'type': 'gauge'},
    ],
}

# https://docs.snowflake.com/en/sql-reference/organization-usage/storage_daily_history.html
OrgStorageDaily = {
    'name': 'organization.storage.metrics',
    'query': (
        'select ACCOUNT_NAME, sum(AVERAGE_BYTES), sum(CREDITS) from STORAGE_DAILY_HISTORY '
        'where USAGE_DATE = DATEADD(day, -1, current_date) group by 1;'
    ),
    'columns': [
        {'name': 'billing_account', 'type': 'tag'},
        {'name': 'organization.storage.average_bytes', 'type': 'gauge'},
        {'name': 'organization.storage.credits', 'type': 'gauge'},
    ],
}


# https://docs.snowflake.com/en/sql-reference/organization-usage/remaining_balance_daily.html
OrgBalance = {
    'name': 'organization.balance.metrics',
    'query': (
        'select CONTRACT_NUMBER, CURRENCY, sum(FREE_USAGE_BALANCE), sum(CAPACITY_BALANCE), '
        'sum(ON_DEMAND_CONSUMPTION_BALANCE), sum(ROLLOVER_BALANCE) from REMAINING_BALANCE_DAILY '
        'where DATE = DATEADD(day, -1, current_date) group by 1, 2;'
    ),
    'columns': [
        {'name': 'contract_number', 'type': 'tag'},
        {'name': 'currency', 'type': 'tag'},
        {'name': 'organization.balance.free_usage', 'type': 'gauge'},
        {'name': 'organization.balance.capacity', 'type': 'gauge'},
        {'name': 'organization.balance.on_demand_consumption', 'type': 'gauge'},
        {'name': 'organization.balance.rollover', 'type': 'gauge'},
    ],
}

# https://docs.snowflake.com/en/sql-reference/organization-usage/rate_sheet_daily.html
OrgRateSheet = {
    'name': 'organization.rate.metrics',
    'query': (
        'select CONTRACT_NUMBER, ACCOUNT_NAME, USAGE_TYPE, SERVICE_TYPE, CURRENCY, '
        'sum(EFFECTIVE_RATE) from RATE_SHEET_DAILY '
        'where DATE = DATEADD(day, -1, current_date) group by 1, 2, 3, 4, 5;'
    ),
    'columns': [
        {'name': 'contract_number', 'type': 'tag'},
        {'name': 'billing_account', 'type': 'tag'},
        {'name': 'usage_type', 'type': 'tag'},
        {'name': 'service_type', 'type': 'tag'},
        {'name': 'currency', 'type': 'tag'},
        {'name': 'organization.rate.effective_rate', 'type': 'gauge'},
    ],
}

# https://docs.snowflake.com/en/sql-reference/organization-usage/data_transfer_history.html
OrgDataTransfer = {
    'name': 'organization.data_transfer.metrics',
    'query': (
        'select ACCOUNT_NAME, SOURCE_CLOUD, TARGET_CLOUD, TRANSFER_TYPE, '
        'sum(BYTES_TRANSFERRED) from DATA_TRANSFER_HISTORY '
        'where USAGE_DATE = DATEADD(day, -1, current_date) group by 1, 2, 3, 4;'
    ),
    'columns': [
        {'name': 'billing_account', 'type': 'tag'},
        {'name': 'source_cloud', 'type': 'tag'},
        {'name': 'target_cloud', 'type': 'tag'},
        {'name': 'transfer_type', 'type': 'tag'},
        {'name': 'organization.data_transfer.bytes_transferred', 'type': 'gauge'},
    ],
}
