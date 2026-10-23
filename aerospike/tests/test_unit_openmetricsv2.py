# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from pathlib import Path

import pytest

from datadog_checks.aerospike import AerospikeCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import (
    EXPECTED_PROMETHEUS_METRICS,
    EXPECTED_PROMETHEUS_METRICS_5_6,
    HERE,
    PROMETHEUS_XDR_METRICS,
)

pytestmark = [pytest.mark.unit]


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


def test_openmetricsv2_check(aggregator, dd_run_check, instance_openmetrics_v2, fake_http, fake_http_response):
    fake_http_response(
        instance_openmetrics_v2['openmetrics_endpoint'], Path(get_fixture_path('prometheus.txt')).read_bytes()
    )

    check = AerospikeCheck('aerospike', {}, [instance_openmetrics_v2])
    dd_run_check(check)

    for metric_name in EXPECTED_PROMETHEUS_METRICS + EXPECTED_PROMETHEUS_METRICS_5_6 + PROMETHEUS_XDR_METRICS:
        aggregator.assert_metric(metric_name)

        aggregator.assert_metric_has_tag(
            metric_name, 'endpoint:{}'.format(instance_openmetrics_v2.get('openmetrics_endpoint'))
        )
        aggregator.assert_metric_has_tag(metric_name, 'aerospike_cluster:null')
        aggregator.assert_metric_has_tag(metric_name, 'aerospike_service:192.168.32.3:3000')

    fake_http.assert_all_responses_consumed()
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
