# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from six import PY2

from datadog_checks.dev.utils import get_metadata_metrics

from .common import PROMETHEUS_METRICS


@pytest.mark.skipif(PY2, reason='OpenMetrics V2 is only available with Python 3')
def test_omv2_check(aggregator, omv2_instance_use_openmetrics, mock_prometheus_data, dd_run_check, check_v2):
    c = check_v2(omv2_instance_use_openmetrics(True))
    dd_run_check(c)
    for m in PROMETHEUS_METRICS:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
