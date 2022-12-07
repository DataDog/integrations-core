import pytest

from datadog_checks.cloudera import ClouderaCheck
from datadog_checks.cloudera.metrics import METRICS
from datadog_checks.dev.utils import get_metadata_metrics


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    # Given
    # When
    aggregator = dd_agent_check(instance)
    # Then
    for category, metrics in METRICS.items():
        for metric in metrics:
            aggregator.assert_metric(f'cloudera.{category}.{metric}')
    aggregator.assert_service_check('cloudera.can_connect', ClouderaCheck.OK)
    # caddy test env is supposed to be in BAD_HEALTH
    aggregator.assert_service_check('cloudera.cluster.health', ClouderaCheck.CRITICAL, message="BAD_HEALTH")
    aggregator.assert_service_check('cloudera.host.health', ClouderaCheck.OK)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
