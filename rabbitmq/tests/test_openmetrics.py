from pathlib import Path

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.rabbitmq import RabbitMQ

from .common import DEFAULT_OM_TAGS, HERE
from .metrics import DEFAULT_OPENMETRICS

OPENMETRICS_RESPONSE_FIXTURES = HERE / Path('fixtures')


def test_aggregated_endpoint(aggregator, dd_run_check, mock_http_response):
    """User only enables aggregated endpoint.

    We expect in this case all the metrics from the '/metrics' endpoint.
    """
    mock_http_response(file_path=OPENMETRICS_RESPONSE_FIXTURES / "metrics.txt")
    check = RabbitMQ(
        "rabbitmq",
        {},
        [{'prometheus_plugin': {'url': "localhost:15692", "include_aggregated_endpoint": True}, "metrics": [".+"]}],
    )
    dd_run_check(check)

    build_info_tags = [
        'erlang_version:25.1.2',
        'prometheus_client_version:4.9.1',
        'prometheus_plugin_version:3.11.3',
        'rabbitmq_version:3.11.3',
    ]
    identity_info_tags = [
        'rabbitmq_node:rabbit@54cfac2199f1',
        "rabbitmq_cluster:rabbit@54cfac2199f1",
        "rabbitmq_cluster_permanent_id:rabbitmq-cluster-id-cyw_z6c4UMIBoK51iVq9rw",
    ]

    for m in DEFAULT_OPENMETRICS:
        aggregator.assert_metric(m)

    aggregator.assert_metric('rabbitmq.build_info', tags=DEFAULT_OM_TAGS + build_info_tags)
    aggregator.assert_metric('rabbitmq.identity_info', tags=DEFAULT_OM_TAGS + identity_info_tags)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()
