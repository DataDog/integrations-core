# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base.utils.db import Query


# https://docs.snowflake.com/en/sql-reference/account-usage/storage_usage.html
# Grab
StorageUsageMetrics = Query(
    {
        'name': 'storage.metrics',
        'query': 'SELECT STORAGE_BYTES, STAGE_BYTES, FAILSAFE_BYTES from STORAGE_USAGE ORDER BY USAGE_DATE DESC LIMIT 1;',
        'columns': [
            {'name': 'storage.storage_bytes', 'type': 'gauge'},
            {'name': 'storage.stage_bytes', 'type': 'gauge'},
            {'name': 'storage.failsafe_bytes', 'type': 'gauge'},
        ],
    }
)