# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

DiskUsage = {
    'name': 'disk_usage',
    'query': (
        'SELECT ASP_NUMBER, UNIT_NUMBER, UNIT_TYPE, UNIT_STORAGE_CAPACITY, '
        'UNIT_SPACE_AVAILABLE, PERCENT_USED FROM QSYS2.SYSDISKSTAT'
    ),
    'columns': [
        {'name': 'asp_number', 'type': 'tag'},
        {'name': 'unit_number', 'type': 'tag'},
        {'name': 'unit_type', 'type': 'tag'},
        {'name': 'disk.unit_storage_capacity', 'type': 'gauge'},
        {'name': 'disk.unit_space_available', 'type': 'gauge'},
        {'name': 'disk.percent_used', 'type': 'gauge'},
    ],
}
