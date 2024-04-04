# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from itertools import product
from pathlib import Path
from urllib.parse import urlparse

import pytest

from datadog_checks.base.errors import ConfigurationError
from datadog_checks.base.types import ServiceCheck
from datadog_checks.dev.http import MockResponse
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.rabbitmq import RabbitMQ

from .common import HERE
from .metrics import AGGREGATED_ONLY_METRICS, DEFAULT_OPENMETRICS, MISSING_OPENMETRICS, SUMMARY_METRICS

OM_RESPONSE_FIXTURES = HERE / Path('fixtures')
TEST_URL = "http://localhost:15692"
OM_ENDPOINT_TAG = f"endpoint:{TEST_URL}/metrics"
BUILD_INFO_TAGS = [
    'erlang_version:25.1.2',
    'prometheus_client_version:4.9.1',
    'prometheus_plugin_version:3.11.3',
    'rabbitmq_version:3.11.3',
]
IDENTITY_INFO_TAGS = [
    'rabbitmq_node:rabbit@54cfac2199f1',
    "rabbitmq_cluster:rabbit@54cfac2199f1",
    "rabbitmq_cluster_permanent_id:rabbitmq-cluster-id-cyw_z6c4UMIBoK51iVq9rw",
]


def _rmq_om_check(prom_plugin_settings):
    return RabbitMQ("rabbitmq", {}, [{'prometheus_plugin': prom_plugin_settings}])


def _common_assertions(aggregator):
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('rabbitmq.openmetrics.health', status=ServiceCheck.OK)


@pytest.mark.parametrize(
    'aggregated_setting',
    [
        pytest.param({"include_aggregated_endpoint": True}, id="explicitly enable"),
        pytest.param({}, id="implicitly enable by default"),
    ],
)
def test_aggregated_endpoint(aggregated_setting, aggregator, dd_run_check, mock_http_response):
    """User only enables aggregated endpoint.

    We expect in this case all the metrics from the '/metrics' endpoint.
    """
    mock_http_response(file_path=OM_RESPONSE_FIXTURES / "metrics.txt")
    prometheus_settings = {'url': TEST_URL, **aggregated_setting}
    check = _rmq_om_check(prometheus_settings)
    dd_run_check(check)

    for m in DEFAULT_OPENMETRICS:
        aggregator.assert_metric(m)
        for tag in IDENTITY_INFO_TAGS:
            aggregator.assert_metric_has_tag(m, tag)

    for m in MISSING_OPENMETRICS:
        aggregator.assert_metric(m, at_least=0)

    aggregator.assert_metric('rabbitmq.build_info', tags=[OM_ENDPOINT_TAG] + BUILD_INFO_TAGS + IDENTITY_INFO_TAGS)
    aggregator.assert_metric('rabbitmq.identity_info', tags=[OM_ENDPOINT_TAG] + IDENTITY_INFO_TAGS)
    _common_assertions(aggregator)


def test_aggregated_endpoint_as_per_object(aggregator, dd_run_check, mock_http_response):
    """Rabbitmq is configured to emit per-object metrics from the `/metrics` endpoint.

    We expect all metrics except the ones unique to the `/metrics` endpoint to be collected.
    """
    mock_http_response(file_path=OM_RESPONSE_FIXTURES / "per-object.txt")
    prometheus_settings = {'url': TEST_URL}
    check = _rmq_om_check(prometheus_settings)
    dd_run_check(check)

    for m in DEFAULT_OPENMETRICS - AGGREGATED_ONLY_METRICS:
        aggregator.assert_metric(m)
        for tag in IDENTITY_INFO_TAGS:
            aggregator.assert_metric_has_tag(m, tag)

    for m in MISSING_OPENMETRICS:
        aggregator.assert_metric(m, at_least=0)

    aggregator.assert_metric('rabbitmq.build_info', tags=[OM_ENDPOINT_TAG] + BUILD_INFO_TAGS + IDENTITY_INFO_TAGS)
    aggregator.assert_metric('rabbitmq.identity_info', tags=[OM_ENDPOINT_TAG] + IDENTITY_INFO_TAGS)
    _common_assertions(aggregator)


@pytest.mark.parametrize(
    'endpoint, fixture_file, expected_metrics',
    [
        pytest.param("detailed", 'detailed.txt', set(), id="detailed, no query"),
        pytest.param(
            'detailed?family=queue_coarse_metrics',
            "detailed-queue_coarse_metrics.txt",
            {
                'rabbitmq.queue.messages',
                'rabbitmq.queue.messages.ready',
                'rabbitmq.queue.messages.unacked',
                'rabbitmq.queue.process_reductions.count',
            },
            id="detailed, query queue_coarse_metrics family",
        ),
    ],
)
def test_unaggregated_endpoint(endpoint, fixture_file, expected_metrics, aggregator, dd_run_check, mock_http_response):
    """User only enables unaggregated endpoint, e.g. '/metrics/per-object' or '/metrics/detailed'.

    We expect in this case only the metrics for the unaggregated endpoint, nothing from '/metrics'.
    """
    mock_http_response(file_path=OM_RESPONSE_FIXTURES / fixture_file)
    check = _rmq_om_check(
        {
            'url': TEST_URL,
            'unaggregated_endpoint': endpoint,
            "include_aggregated_endpoint": False,
        }
    )
    dd_run_check(check)

    for m in expected_metrics:
        aggregator.assert_metric(m)
        for tag in IDENTITY_INFO_TAGS:
            aggregator.assert_metric_has_tag(m, tag)

    for m in (DEFAULT_OPENMETRICS - expected_metrics) | MISSING_OPENMETRICS:
        # We check that all metrics that are not in the query don't show up at all.
        aggregator.assert_metric(m, at_least=0)
    aggregator.assert_metric(
        'rabbitmq.build_info', tags=[OM_ENDPOINT_TAG + f"/{endpoint}"] + BUILD_INFO_TAGS + IDENTITY_INFO_TAGS
    )
    aggregator.assert_metric('rabbitmq.identity_info', tags=[OM_ENDPOINT_TAG + f"/{endpoint}"] + IDENTITY_INFO_TAGS)
    _common_assertions(aggregator)


def mock_http_responses(url, **_params):
    parsed = urlparse(url)
    fname = {
        '/metrics': 'metrics.txt',
        '/metrics/per-object': 'per-object.txt',
        '/metrics/detailed?family=queue_consumer_count': 'detailed-queue_consumer_count.txt',
        '/metrics/detailed?family=queue_consumer_count&vhost=test': 'detailed-queue_consumer_count.txt',
        (
            '/metrics/detailed?family=queue_consumer_count' '&family=queue_coarse_metrics'
        ): 'detailed-queue_coarse_metrics-queue_consumer_count.txt',
        (
            '/metrics/detailed?family=vhost_status&family=exchange_names&family=exchange_bindings'
        ): 'detailed-only-metrics.txt',
    }[parsed.path + (f"?{parsed.query}" if parsed.query else "")]
    with open(OM_RESPONSE_FIXTURES / fname) as fh:
        return MockResponse(content=fh.read())


@pytest.mark.parametrize(
    'endpoint, metrics',
    [
        pytest.param(
            'detailed?family=queue_consumer_count',
            ['rabbitmq.queue.consumers'],
            id='detailed?family=queue_consumer_count',
        ),
        pytest.param(
            'detailed?family=queue_consumer_count&vhost=test',
            ['rabbitmq.queue.consumers'],
            id='detailed?family=queue_consumer_count&vhost=test',
        ),
        pytest.param(
            'detailed?family=queue_consumer_count&family=queue_coarse_metrics',
            [
                'rabbitmq.queue.consumers',
                'rabbitmq.queue.messages',
                'rabbitmq.queue.messages.ready',
                'rabbitmq.queue.messages.unacked',
                'rabbitmq.queue.process_reductions.count',
            ],
            id="two metric families",
        ),
    ],
)
def test_aggregated_and_unaggregated_endpoints(endpoint, metrics, aggregator, dd_run_check, mocker):
    """Detailed and aggregated endpoints queried together.

    We will drop duplicate metrics coming from both endpoints in favor of the
    detailed ones as they can provide more information.
    """
    check = _rmq_om_check(
        {
            'url': "http://localhost:15692",
            'unaggregated_endpoint': endpoint,
            'include_aggregated_endpoint': True,
        }
    )
    mocker.patch('requests.get', wraps=mock_http_responses)
    dd_run_check(check)

    meta_metrics = {'rabbitmq.build_info', 'rabbitmq.identity_info'}

    for m in metrics:
        aggregator.assert_metric_has_tag(m, f'endpoint:http://localhost:15692/metrics/{endpoint}', at_least=1)
        # Here we want to make sure that we don't collect the equivalent metrics from
        # the aggregated endpoint.
        aggregator.assert_metric_has_tag(m, 'endpoint:http://localhost:15692/metrics', count=0)
    for m in (DEFAULT_OPENMETRICS.difference(metrics) - SUMMARY_METRICS) - meta_metrics:
        # We check the equivalent for metrics that come from the aggregated endpoint.
        aggregator.assert_metric_has_tag(m, f'endpoint:http://localhost:15692/metrics/{endpoint}', count=0)
        aggregator.assert_metric_has_tag(m, 'endpoint:http://localhost:15692/metrics', at_least=1)
    # Summary metrics MAY come from both endpoints or from only one, so we just make sure at least one is submitted.
    for m in SUMMARY_METRICS:
        aggregator.assert_metric(m, at_least=1)
    # Identity and build info metrics should come from both endpoints.
    for m, tag in product(
        meta_metrics,
        [
            f'endpoint:http://localhost:15692/metrics/{endpoint}',
            'endpoint:http://localhost:15692/metrics',
        ],
    ):
        aggregator.assert_metric_has_tag(m, tag, count=1)
    _common_assertions(aggregator)


def test_detailed_only_metrics(aggregator, dd_run_check, mocker):
    """Metrics that only appear in detailed endpoint.

    Most metric families have metrics that are both in per-obj and detailed endpoints.
    A few, however, only expose metrics in the detailed endpoint.
    This means they show up without a `detailed` prefix.
    """
    endpoint = 'detailed?family=vhost_status&family=exchange_names&family=exchange_bindings'
    check = _rmq_om_check(
        {
            'url': "http://localhost:15692",
            'unaggregated_endpoint': endpoint,
            'include_aggregated_endpoint': True,
        }
    )
    mocker.patch('requests.get', wraps=mock_http_responses)
    dd_run_check(check)

    detailed_only_metrics = (
        'rabbitmq.cluster.vhost_status',
        'rabbitmq.cluster.exchange_bindings',
        'rabbitmq.cluster.exchange_name',
    )
    for m in detailed_only_metrics:
        aggregator.assert_metric(m, metric_type=aggregator.GAUGE)


@pytest.mark.parametrize(
    'prom_plugin_settings, err',
    [
        pytest.param({}, r"'prometheus_plugin\.url' field is required\.", id="No URL supplied."),
        pytest.param(
            {'url': 'localhost'},
            r"'prometheus_plugin\.url' field must be an HTTP or HTTPS URL\.",
            id="URL supplied without HTTP(S) protocol.",
        ),
        pytest.param(
            {'url': "http://localhost", "unaggregated_endpoint": "detailed?"},
            r"'prometheus_plugin\.unaggregated_endpoint' must be 'detailed', or 'detailed\?<QUERY>'\.",
            id="Invalid nonempty unaggregated_endpoint value.",
        ),
        pytest.param(
            {'url': "http://localhost", "unaggregated_endpoint": ""},
            r"'prometheus_plugin\.unaggregated_endpoint' must be 'detailed', or 'detailed\?<QUERY>'\.",
            id="Empty unaggregated_endpoint value is invalid.",
        ),
        pytest.param(
            {'url': "http://localhost", "unaggregated_endpoint": "per-object"},
            r"'prometheus_plugin\.unaggregated_endpoint' must be 'detailed', or 'detailed\?<QUERY>'\.",
            id="We do not support per-object endpoint in the config.",
        ),
        pytest.param(
            {'url': "http://localhost", "unaggregated_endpoint": []},
            "Input should be a valid string",
            id="Unaggregated_endpoint value must be a string.",
        ),
        pytest.param(
            {'url': "http://localhost", "include_aggregated_endpoint": 1},
            r"'prometheus_plugin\.include_aggregated_endpoint' must be a boolean\.",
            id="Aggregated_endpoint must be a boolean.",
        ),
        pytest.param(
            {'url': "http://localhost", "include_aggregated_endpoint": False},
            r"'prometheus_plugin\.include_aggregated_endpoint' field must be set to 'true' "
            + r"when 'prometheus_plugin\.unaggregated_endpoint' is not collected\.",
            id="include_aggregated_endpoint must be true when unaggregated_endpoint is missing.",
        ),
    ],
)
def test_config(prom_plugin_settings, err):
    check = _rmq_om_check(prom_plugin_settings)
    with pytest.raises(ConfigurationError, match=err):
        check.load_configuration_models()


def test_service_check_critical(aggregator, dd_run_check, mock_http_response):
    mock_http_response(status_code=404)
    check = _rmq_om_check({'url': 'http://fail'})
    with pytest.raises(Exception, match="requests.exceptions.HTTPError"):
        dd_run_check(check)
    aggregator.assert_service_check('rabbitmq.openmetrics.health', status=check.CRITICAL)
