# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.dev.testing import requires_py2, requires_py3
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.envoy.metrics import PROMETHEUS_METRICS_MAP

from .common import DEFAULT_INSTANCE, MOCKED_PROMETHEUS_METRICS, get_fixture_path

pytestmark = [pytest.mark.unit]


def test_unique_metrics():
    duplicated_metrics = set()

    for value in PROMETHEUS_METRICS_MAP.values():
        # We only have string with envoy so far
        assert isinstance(value, str)
        assert value not in duplicated_metrics, "metric `{}` already declared".format(value)
        duplicated_metrics.add(value)


@requires_py2
def test_check_with_py2(aggregator, dd_run_check, check, mock_http_response):
    with pytest.raises(ConfigurationError, match="This version of the integration is only available when using py3."):
        check(DEFAULT_INSTANCE)


@requires_py3
def test_check(aggregator, dd_run_check, check, mock_http_response):
    mock_http_response(file_path=get_fixture_path('openmetrics.txt'))

    c = check(DEFAULT_INSTANCE)

    dd_run_check(c)

    for metric in MOCKED_PROMETHEUS_METRICS:
        aggregator.assert_metric("envoy.{}".format(metric))

    aggregator.assert_service_check(
        "envoy.openmetrics.health", status=AgentCheck.OK, tags=['endpoint:http://localhost:8001/stats/prometheus']
    )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_no_duplicate_metrics()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@requires_py3
def test_collect_metadata(datadog_agent, fixture_path, mock_http_response, check, default_instance):
    c = check(default_instance)
    c.check_id = 'test:123'
    c.log = mock.MagicMock()

    mock_http_response(file_path=fixture_path('server_info_api_v3'))

    c._collect_metadata()

    version_metadata = {
        'version.scheme': 'semver',
        'version.major': "1",
        'version.minor': "18",
        'version.patch': "3",
        'version.raw': '1.18.3',
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(len(version_metadata))


@requires_py3
def test_collect_metadata_with_invalid_base_url(
    datadog_agent, fixture_path, mock_http_response, check, default_instance
):
    default_instance["openmetrics_endpoint"] = None
    c = check(default_instance)
    c.check_id = 'test:123'
    c.log = mock.MagicMock()

    c._collect_metadata()
    datadog_agent.assert_metadata_count(0)
    c.log.debug.assert_called_with('Skipping server info collection due to malformed url: %s', b'')
