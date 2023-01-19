from itertools import product
from pathlib import Path

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.rabbitmq import RabbitMQ

from .common import DEFAULT_OM_TAGS, HERE
from .metrics import DEFAULT_OPENMETRICS, MISSING_OPENMETRICS

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

    for m in MISSING_OPENMETRICS:
        aggregator.assert_metric(m, at_least=0)

    aggregator.assert_metric('rabbitmq.build_info', tags=DEFAULT_OM_TAGS + build_info_tags)
    aggregator.assert_metric('rabbitmq.identity_info', tags=DEFAULT_OM_TAGS + identity_info_tags)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()


def test_bare_detailed_endpoint(aggregator, dd_run_check, mock_http_response):
    """User enables only the /metrics/detailed endpoint and without any query to it.

    We expect at least metrics like build_info and identity_info to still be present.
    """
    mock_http_response(file_path=OPENMETRICS_RESPONSE_FIXTURES / "detailed.txt")
    check = RabbitMQ(
        "rabbitmq",
        {},
        [
            {
                'prometheus_plugin': {
                    'url': "localhost:15692",
                    'unaggregated_endpoint': 'detailed',
                },
                "metrics": [".+"],
            }
        ],
    )
    dd_run_check(check)
    expected_metrics = [
        dict(
            name='rabbitmq.build_info',
            value=1,
            metric_type=aggregator.GAUGE,
            tags=[
                'erlang_version:25.1.2',
                'prometheus_client_version:4.9.1',
                'prometheus_plugin_version:3.11.3',
                'rabbitmq_version:3.11.3',
            ],
        ),
        dict(
            name='rabbitmq.identity_info',
            value=1,
            metric_type=aggregator.GAUGE,
            tags=[
                'rabbitmq_node:rabbit@54cfac2199f1',
                "rabbitmq_cluster:rabbit@54cfac2199f1",
                "rabbitmq_cluster_permanent_id:rabbitmq-cluster-id-cyw_z6c4UMIBoK51iVq9rw",
            ],
        ),
    ]
    for m in expected_metrics:
        kwargs = {**m, "tags": ["endpoint:localhost:15692/metrics/detailed"] + m.get('tags', [])}
        aggregator.assert_metric(**kwargs)


def test_detailed_endpoint_queue_coarse_metrics(aggregator, dd_run_check, mock_http_response):
    """We scrape the /metrics/detailed endpoint with the 'queue_coarse_metrics' family query."""
    mock_http_response(file_path=OPENMETRICS_RESPONSE_FIXTURES / "detailed-queue_coarse_metrics.txt")
    check = RabbitMQ(
        "rabbitmq",
        {},
        [
            {
                'prometheus_plugin': {
                    'url': "localhost:15692",
                    'unaggregated_endpoint': 'detailed?family=queue_coarse_metrics',
                },
                "metrics": [".+"],
            }
        ],
    )
    dd_run_check(check)

    expected_metrics = (
        [
            dict(
                name='rabbitmq.build_info',
                value=1,
                metric_type=aggregator.GAUGE,
                tags=[
                    'erlang_version:25.1.2',
                    'prometheus_client_version:4.9.1',
                    'prometheus_plugin_version:3.11.3',
                    'rabbitmq_version:3.11.3',
                ],
            ),
            dict(
                name='rabbitmq.identity_info',
                value=1,
                metric_type=aggregator.GAUGE,
                tags=[
                    'rabbitmq_node:rabbit@54cfac2199f1',
                    "rabbitmq_cluster:rabbit@54cfac2199f1",
                    "rabbitmq_cluster_permanent_id:rabbitmq-cluster-id-cyw_z6c4UMIBoK51iVq9rw",
                ],
            ),
        ]
        + [
            dict(
                name=name,
                value=value,
                metric_type=aggregator.GAUGE,
                tags=['vhost:/', f'queue:{qname}'],
            )
            for name, (value, qname) in product(
                ('rabbitmq.queue.messages', 'rabbitmq.queue.messages.ready'),
                ((0, 'queue1'), (1, 'queue2'), (0, 'queue3')),
            )
        ]
        + [
            dict(
                name='rabbitmq.queue.messages.unacked',
                value=0,
                metric_type=aggregator.GAUGE,
                tags=['vhost:/', f'queue:{qname}'],
            )
            for qname in ('queue1', 'queue2', 'queue3')
        ]
        + [
            dict(
                name='rabbitmq.queue.process_reductions.count',
                value=value,
                metric_type=aggregator.MONOTONIC_COUNT,
                tags=['vhost:/', f'queue:{qname}'],
            )
            for qname, value in (('queue1', 30773), ('queue2', 30466), ('queue3', 35146))
        ]
    )
    for m in expected_metrics:
        kwargs = {
            **m,
            "tags": ["endpoint:localhost:15692/metrics/detailed?family=queue_coarse_metrics"] + m.get('tags', []),
        }
        aggregator.assert_metric(**kwargs)


def test_per_object(aggregator, dd_run_check, mock_http_response):
    """We scrape the /metrics/per-object endpoint."""
    mock_http_response(file_path=OPENMETRICS_RESPONSE_FIXTURES / "per-object.txt")
    check = RabbitMQ(
        "rabbitmq",
        {},
        [
            {
                'prometheus_plugin': {
                    'url': "localhost:15692",
                    'unaggregated_endpoint': 'per-object',
                },
                "metrics": [".+"],
            }
        ],
    )
    dd_run_check(check)

    expected_metrics = (
        [
            dict(
                name='rabbitmq.build_info',
                value=1,
                metric_type=aggregator.GAUGE,
                tags=[
                    'erlang_version:25.1.2',
                    'prometheus_client_version:4.9.1',
                    'prometheus_plugin_version:3.11.3',
                    'rabbitmq_version:3.11.3',
                ],
            ),
            dict(
                name='rabbitmq.identity_info',
                value=1,
                metric_type=aggregator.GAUGE,
                tags=[
                    'rabbitmq_node:rabbit@54cfac2199f1',
                    "rabbitmq_cluster:rabbit@54cfac2199f1",
                    "rabbitmq_cluster_permanent_id:rabbitmq-cluster-id-cyw_z6c4UMIBoK51iVq9rw",
                ],
            ),
        ]
        + [
            dict(
                name=name,
                value=value,
                metric_type=aggregator.GAUGE,
                tags=['vhost:/', f'queue:{qname}'],
            )
            for name, (value, qname) in product(
                ('rabbitmq.queue.messages', 'rabbitmq.queue.messages.ready'),
                ((0, 'queue1'), (1, 'queue2'), (0, 'queue3')),
            )
        ]
        + [
            dict(
                name='rabbitmq.queue.messages.unacked',
                value=0,
                metric_type=aggregator.GAUGE,
                tags=['vhost:/', f'queue:{qname}'],
            )
            for qname in ('queue1', 'queue2', 'queue3')
        ]
        + [
            dict(
                name='rabbitmq.queue.process_reductions.count',
                value=value,
                metric_type=aggregator.MONOTONIC_COUNT,
                tags=['vhost:/', f'queue:{qname}'],
            )
            for qname, value in (('queue1', 34258), ('queue2', 38325), ('queue3', 30020))
        ]
    )
    for m in expected_metrics:
        kwargs = {
            **m,
            "tags": ["endpoint:localhost:15692/metrics/per-object"] + m.get('tags', []),
        }
        aggregator.assert_metric(**kwargs)
