import pytest

from datadog_checks.cloudera import ClouderaCheck
from datadog_checks.cloudera.metrics import TIMESERIES_METRICS

from .common import CAN_CONNECT_TAGS, CLUSTER_HEALTH_TAGS, METRICS


@pytest.mark.e2e
def test_e2e(dd_agent_check, config):
    # Given
    # When
    aggregator = dd_agent_check(config)
    # Then
    for category, metrics in METRICS.items():
        for metric in metrics:
            aggregator.assert_metric(f'cloudera.{category}.{metric}', at_least=1)
            aggregator.assert_metric_has_tag_prefix(f'cloudera.{category}.{metric}', "cloudera_cluster")
            aggregator.assert_metric_has_tag(f'cloudera.{category}.{metric}', "test1")

            # Only non-cluster metrics have rack_id tags
            if category != 'cluster':
                aggregator.assert_metric_has_tag_prefix(f'cloudera.{category}.{metric}', "cloudera_rack_id")

    # All timeseries metrics should have cloudera_{category} tag
    for category, metrics in TIMESERIES_METRICS.items():
        for metric in metrics:
            aggregator.assert_metric_has_tag_prefix(f'cloudera.{category}.{metric}', f"cloudera_{category}")

    aggregator.assert_service_check(
        'cloudera.can_connect',
        ClouderaCheck.OK,
        tags=CAN_CONNECT_TAGS,
    )
    # caddy test env is supposed to be in BAD_HEALTH
    aggregator.assert_service_check(
        'cloudera.cluster.health',
        ClouderaCheck.CRITICAL,
        message="BAD_HEALTH",
        tags=CLUSTER_HEALTH_TAGS,
    )
    aggregator.assert_service_check('cloudera.host.health', ClouderaCheck.OK)
    aggregator.assert_event(
        "ExecutionException running extraction tasks for service 'cod--qfdcinkqrzw::yarn'.", count=1
    )
    aggregator.assert_all_metrics_covered()
