# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from . import common


@pytest.mark.e2e
def test_check(dd_agent_check, check):
    aggregator = dd_agent_check(common.get_config_stubs(".")[0], rate=True)
    for metric in common.DIR_METRICS:
        aggregator.assert_metric(metric, tags=common.EXPECTED_TAGS)
    for metric in common.FILE_METRICS:
        for submetric in ['avg', 'max', 'count', 'median', '95percentile']:
            aggregator.assert_metric('{}.{}'.format(metric, submetric), tags=common.EXPECTED_TAGS)
    aggregator.assert_all_metrics_covered()
