# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from six import PY2

from datadog_checks.dev.utils import get_metadata_metrics

from .common import PROMETHEUS_METRICS, get_fixture_path


@pytest.mark.integration
@pytest.mark.skipif(PY2, reason='OpenMetrics V2 is only available with Python 3')
def test_omv2_check(aggregator, openmetrics_instance, mock_http_response, dd_run_check, teamcity_om_check):
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    check = teamcity_om_check(openmetrics_instance)
    dd_run_check(check)
    for m in PROMETHEUS_METRICS:
        aggregator.assert_metric(m)
        aggregator.assert_metric_has_tag(m, 'endpoint:http://localhost:8111/guestAuth/app/metrics')
        aggregator.assert_metric_has_tag(m, 'nodeId:tc-instance-1')
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check(
        'teamcity.openmetrics.health', check.OK, tags=['endpoint:http://localhost:8111/guestAuth/app/metrics']
    )
