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
