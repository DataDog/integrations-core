# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from decimal import Decimal

STORAGE_USAGE = [(Decimal('0.000000'), Decimal('1206.000000'), Decimal('19.200000'))]
DATABASE_STORAGE_USAGE_HISTORY = [('SNOWFLAKE_DB', Decimal('133.000000'), Decimal('9.100000'))]
METERING_HISTORY = [
    (
        'WAREHOUSE_METERING',
        'COMPUTE_WH',
        Decimal('12.000000000'),
        Decimal('1.000000000'),
        Decimal('0.80397000'),
        Decimal('0.066997500000'),
        Decimal('12.803970000'),
        Decimal('1.066997500000'),
    )
]
WAREHOUSE_METERING_HISTORY = [
    (
        'COMPUTE_WH',
        Decimal('13.000000000'),
        Decimal('1.000000000'),
        Decimal('0.870148056'),
        Decimal('0.066934465846'),
        Decimal('13.870148056'),
        Decimal('1.066934465846'),
    )
]
LOGIN_HISTORY = [('SNOWFLAKE_UI', 2, 6, 8), ('PYTHON_DRIVER', 0, 148, 148)]
WAREHOUSE_LOAD_HISTORY = [('COMPUTE_WH', Decimal('0.000446667'), Decimal('0E-9'), Decimal('0E-9'), Decimal('0E-9'))]
QUERY_HISTORY = [
    (
        'USE',
        'COMPUTE_WH',
        'SNOWFLAKE',
        None,
        Decimal('4.333333'),
        Decimal('24.555556'),
        Decimal('0.000000'),
        Decimal('0.000000'),
        Decimal('0.000000'),
        Decimal('0.000000'),
        Decimal('0.000000'),
    )
]
ORGANIZATION_USAGE_IN_CURRENCY_DAILY = [('test', 'Standard', 'Compute', 'USD', Decimal('0.4'), Decimal('0.7'))]
ORGANIZATION_WAREHOUSE_METERING_HISTORY = [
    (
        'test',
        'account_name',
        Decimal('300'),
        Decimal('3.4'),
        Decimal('902.49003'),
        Decimal('4.9227'),
        Decimal('212.43'),
        Decimal('34.7'),
    )
]

ORGANIZATION_METERING_DAILY_HISTORY = [
    (
        'account_name',
        'Standard',
        Decimal('300'),
        Decimal('3.4'),
        Decimal('902.49003'),
        Decimal('4.9227'),
        Decimal('212.43'),
        Decimal('34.7'),
        Decimal('342.8321'),
        Decimal('1.7'),
        Decimal('21.02'),
        Decimal('2.9'),
    ),
]

ORGANIZATION_CONTRACT_ITEMS = [
    (
        Decimal('4'),
        'Free Usage',
        'USD',
        Decimal('23'),
    ),
]

ORGANIZATION_STORAGE_DAILY_HISTORY = [
    (
        'account_name',
        Decimal('4510'),
        Decimal('349'),
    ),
]

ORGANIZATION_REMAINING_BALANCE_DAILY = [
    (
        Decimal('4'),
        'USD',
        Decimal('23410'),
        Decimal('814349'),
        Decimal('-35435'),
        Decimal('455435'),
    ),
]

ORGANIZATION_RATE_SHEET_DAILY = [
    (
        Decimal('3'),
        'test_account',
        'usage',
        'service',
        'USD',
        Decimal('312'),
    ),
]

ORGANIZATION_DATA_TRANSFER_HISTORY = [
    (
        'test_account',
        'AWS',
        'GCP',
        'COPY',
        Decimal('13.56'),
    ),
]
