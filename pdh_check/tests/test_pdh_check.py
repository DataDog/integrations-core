# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.stubs import aggregator
from datadog_checks.pdh_check import PDHCheck

# for reasons unknown, flake8 says that pdh_mocks_fixture is unused, even though
# it's used below.  noqa to suppress that error.
from datadog_test_libs.win.pdh_mocks import pdh_mocks_fixture, initialize_pdh_tests  # noqa: F401

CHECK_NAME = 'pdh_check'

INSTANCE = {
    'countersetname': 'System',
    'metrics': [
        ['File Read Operations/sec', 'pdh.system.file_read_per_sec', 'gauge'],
        ['File Write Bytes/sec', 'pdh.system.file_write_bytes_sec', 'gauge'],
    ]
}

INSTANCE_METRICS = [
    'pdh.system.file_read_per_sec',
    'pdh.system.file_write_bytes_sec',
]


@pytest.fixture
def Aggregator():
    aggregator.reset()
    return aggregator


# flake8 then says this is a redefinition of unused, which it's not.
@pytest.mark.usefixtures("pdh_mocks_fixture")  # noqa: F811
def test_basic_check(Aggregator, pdh_mocks_fixture):
    """
    Returns the right metrics and service checks
    """
    # Set up & run the check
    config = {
        'instances': [INSTANCE]
    }
    initialize_pdh_tests()
    c = PDHCheck(CHECK_NAME, {}, {}, config['instances'])
    c.check(config['instances'][0])

    for metric in INSTANCE_METRICS:
        Aggregator.assert_metric(metric, tags=None, count=1)

    Aggregator.assert_all_metrics_covered()
