# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.active_directory.check import SERVICE_METRIC_MAP, ActiveDirectoryCheckV2
from datadog_checks.active_directory.metrics import METRICS_CONFIG
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.testing import requires_windows
from datadog_checks.dev.utils import get_metadata_metrics

# Import the mock data we will use for our tests
from .common import PERFORMANCE_OBJECTS

pytestmark = [requires_windows]


@pytest.fixture
def mock_service_states(mocker):
    """
    Mocks the _service_exists function.
    """

    def _mock_services(service_states):
        def service_exists_mock(service_name):
            return service_states.get(service_name, False)

        return mocker.patch('datadog_checks.active_directory.check._service_exists', side_effect=service_exists_mock)

    return _mock_services


def assert_metrics(aggregator, global_tags, service_states):
    # NTDS metrics are included by default
    for metric in METRICS_CONFIG['NTDS']['counters'][0].values():
        aggregator.assert_metric(f"active_directory.{metric['metric_name']}", 9000, global_tags, count=1)

    for service_name, exists in service_states.items():
        for service_display_name in SERVICE_METRIC_MAP[service_name]:
            service_metric_name = METRICS_CONFIG[service_display_name]['name']
            for metric in METRICS_CONFIG[service_display_name]['counters'][0].values():
                metric_name = ""
                if type(metric) == dict:
                    if 'metric_name' in metric:
                        metric_name = f"active_directory.{metric['metric_name']}"
                    elif 'name' in metric:
                        metric_name = f"active_directory.{service_metric_name}.{metric['name']}"
                elif type(metric) == str:
                    metric_name = f"active_directory.{service_metric_name}.{metric}"
                # Only assert metrics for services that exist
                # If a service doesn't exist, its metrics shouldn't be collected at all
                if exists:
                    aggregator.assert_metric(metric_name, 9000, global_tags, count=1)


@pytest.mark.parametrize(
    'service_states',
    [
        {'Netlogon': True, 'DHCPServer': True, 'DFSR': True},
        {'Netlogon': False, 'DHCPServer': False, 'DFSR': False},
        {'Netlogon': True, 'DHCPServer': False, 'DFSR': False},
        {'Netlogon': False, 'DHCPServer': False, 'DFSR': False},
    ],
)
def test_all_services_existing(
    aggregator,
    dd_run_check,
    mock_performance_objects,
    mock_service_states,
    dd_default_hostname,
    service_states,
):
    """Test metric collection when all services exist."""
    mock_performance_objects(PERFORMANCE_OBJECTS)
    mock_service_states(service_states)
    global_tags = ['server:{}'.format(dd_default_hostname)]

    check = ActiveDirectoryCheckV2("active_directory", {}, [{"host": dd_default_hostname}])
    dd_run_check(check)

    aggregator.assert_service_check('active_directory.windows.perf.health', ServiceCheck.OK, count=1, tags=global_tags)
    assert_metrics(aggregator, global_tags, service_states)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
