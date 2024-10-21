# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import PROMETHEUS_METRICS, PROMETHEUS_METRICS_2023_05_04, get_fixture_path


@pytest.mark.integration
@pytest.mark.parametrize(
    'fixture_path, metrics_set, node_id',
    [
        ('metrics.txt', PROMETHEUS_METRICS, 'nodeId:tc-instance-1'),
        ('metrics2023.05.4.txt', PROMETHEUS_METRICS_2023_05_04, 'nodeId:MAIN_SERVER'),
    ],
)
def test_omv2_check(
    aggregator,
    openmetrics_instance,
    mock_http_response,
    dd_run_check,
    teamcity_om_check,
    fixture_path,
    metrics_set,
    node_id,
):
    mock_http_response(file_path=get_fixture_path(fixture_path))
    check = teamcity_om_check(openmetrics_instance)
    dd_run_check(check)
    for m in metrics_set:
        aggregator.assert_metric(m)
        aggregator.assert_metric_has_tag(m, 'endpoint:http://localhost:8111/guestAuth/app/metrics')
        aggregator.assert_metric_has_tag(m, node_id)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check(
        'teamcity.openmetrics.health', check.OK, tags=['endpoint:http://localhost:8111/guestAuth/app/metrics']
    )
