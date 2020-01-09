# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
from datadog_test_libs.win.pdh_mocks import initialize_pdh_tests, pdh_mocks_fixture  # noqa: F401

from datadog_checks.pdh_check import PDHCheck

from .common import CHECK_NAME, INSTANCE, INSTANCE_METRICS


@pytest.mark.usefixtures('pdh_mocks_fixture')
def test_basic_check(aggregator):
    """
    Returns the right metrics and service checks
    """
    # Set up & run the check
    config = {'instances': [INSTANCE]}
    initialize_pdh_tests()
    c = PDHCheck(CHECK_NAME, {}, {}, config['instances'])
    c.check(config['instances'][0])

    for metric in INSTANCE_METRICS:
        aggregator.assert_metric(metric, tags=None, count=1)

    aggregator.assert_all_metrics_covered()
