# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.aerospike import AerospikeCheck
from datadog_checks.dev.testing import requires_py3
from datadog_checks.dev.utils import get_metadata_metrics

from .common import EXPECTED_PROMETHEUS_METRICS, EXPECTED_PROMETHEUS_METRICS_5_6, HERE, PROMETHEUS_XDR_METRICS

pytestmark = [pytest.mark.unit, requires_py3]


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


def test_openmetricsv2_check(aggregator, dd_run_check, instance_openmetrics_v2, mock_http_response):
    mock_http_response(file_path=get_fixture_path('prometheus.txt'))

    check = AerospikeCheck('aerospike', {}, [instance_openmetrics_v2])
    dd_run_check(check)

    for metric_name in EXPECTED_PROMETHEUS_METRICS + EXPECTED_PROMETHEUS_METRICS_5_6 + PROMETHEUS_XDR_METRICS:
        aggregator.assert_metric(metric_name)

        aggregator.assert_metric_has_tag(
            metric_name, 'endpoint:{}'.format(instance_openmetrics_v2.get('openmetrics_endpoint'))
        )
        aggregator.assert_metric_has_tag(metric_name, 'aerospike_cluster:null')
        aggregator.assert_metric_has_tag(metric_name, 'aerospike_service:192.168.32.3:3000')

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
