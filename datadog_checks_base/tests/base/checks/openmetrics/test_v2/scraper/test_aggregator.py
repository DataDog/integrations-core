# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from ..utils import get_check

GAUGE_PAYLOAD = """
# HELP cars_in_lot The current number of cars in the lot
# TYPE cars_in_lot gauge
cars_in_lot{make="honda", model="civic", color="#FF5733"} 5
cars_in_lot{make="honda", model="civic", color="#4CAF50"} 3
cars_in_lot{make="honda", model="civic", color="#4287f5"} 4
cars_in_lot{make="toyota", model="corolla", color="#FFC300"} 2
cars_in_lot{make="toyota", model="corolla", color="#900C3F"} 3
cars_in_lot{make="toyota", model="corolla", color="#DAF7A6"} 1
cars_in_lot{make="honda", model="civic", license="FF5733"} 5
cars_in_lot{make="honda", model="civic", license="FF5734"} 6
""".strip()

COUNTER_PAYLOAD = """
# HELP car_counter_total The number of cars seen coming into lot
# TYPE car_counter_total counter
car_counter_total{make="honda", model="civic", color="#FF5733"} 120
car_counter_total{make="honda", model="civic", color="#4CAF50"} 95
car_counter_total{make="honda", model="civic", color="#4287f5"} 88
car_counter_total{make="toyota", model="corolla", color="#FFC300"} 70
car_counter_total{make="toyota", model="corolla", color="#900C3F"} 55
car_counter_total{make="toyota", model="corolla", color="#DAF7A6"} 60
""".strip()

SUMMARY_PAYLOAD = """
# HELP rpc_duration RPC latency distributions
# TYPE rpc_duration summary
rpc_duration{handler="api", color="red", quantile="0.5"} 100
rpc_duration{handler="api", color="blue", quantile="0.5"} 80
rpc_duration{handler="api", color="red", quantile="0.99"} 500
rpc_duration{handler="api", color="blue", quantile="0.99"} 400
rpc_duration_sum{handler="api", color="red"} 5000
rpc_duration_sum{handler="api", color="blue"} 3000
rpc_duration_count{handler="api", color="red"} 50
rpc_duration_count{handler="api", color="blue"} 30
""".strip()

HISTOGRAM_PAYLOAD = """
# HELP request_duration A histogram of request durations
# TYPE request_duration histogram
request_duration_bucket{handler="api", color="red", le="0.1"} 10
request_duration_bucket{handler="api", color="blue", le="0.1"} 5
request_duration_bucket{handler="api", color="red", le="1.0"} 20
request_duration_bucket{handler="api", color="blue", le="1.0"} 12
request_duration_bucket{handler="api", color="red", le="+Inf"} 25
request_duration_bucket{handler="api", color="blue", le="+Inf"} 15
request_duration_sum{handler="api", color="red"} 100.5
request_duration_sum{handler="api", color="blue"} 50.3
request_duration_count{handler="api", color="red"} 25
request_duration_count{handler="api", color="blue"} 15
""".strip()


def test_gauge_given_exclude_labels_returns_summed_values_if_present(aggregator, dd_run_check, mock_http_response):
    mock_http_response(GAUGE_PAYLOAD)
    check = get_check({'metrics': ['.+'], 'exclude_labels': ['color'], 'aggregate_metrics_on_label_exclusion': True})
    dd_run_check(check)

    all_metrics = aggregator.metrics('test.cars_in_lot')

    aggregator.assert_metric(
        'test.cars_in_lot',
        12.0,
        metric_type=aggregator.GAUGE,
        tags=['endpoint:test', 'make:honda', 'model:civic'],
    )
    aggregator.assert_metric(
        'test.cars_in_lot',
        6.0,
        metric_type=aggregator.GAUGE,
        tags=['endpoint:test', 'make:toyota', 'model:corolla'],
    )
    for m in all_metrics:
        assert not any(t.startswith('color:') for t in m.tags), f"Excluded tag 'color' found in {m.tags}"

    aggregator.assert_metric(
        'test.cars_in_lot',
        5.0,
        metric_type=aggregator.GAUGE,
        tags=['endpoint:test', 'make:honda', 'model:civic', 'license:FF5733'],
    )
    aggregator.assert_metric(
        'test.cars_in_lot',
        6.0,
        metric_type=aggregator.GAUGE,
        tags=['endpoint:test', 'make:honda', 'model:civic', 'license:FF5734'],
    )
    license_metrics = [m for m in all_metrics if any(t.startswith('license:') for t in m.tags)]
    assert len(license_metrics) == 2

    aggregator.assert_all_metrics_covered()


def test_counter_given_exclude_labels_submits_summed_value(aggregator, dd_run_check, mock_http_response):
    mock_http_response(COUNTER_PAYLOAD)
    check = get_check({'metrics': ['.+'], 'exclude_labels': ['color'], 'aggregate_metrics_on_label_exclusion': True})
    dd_run_check(check)

    aggregator.assert_metric(
        'test.car_counter.count',
        303.0,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'make:honda', 'model:civic'],
    )
    aggregator.assert_metric(
        'test.car_counter.count',
        185.0,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'make:toyota', 'model:corolla'],
    )

    for m in aggregator.metrics('test.car_counter.count'):
        assert not any(t.startswith('color:') for t in m.tags), f"Excluded tag 'color' found in {m.tags}"


def test_counter_given_exclude_labels_submits_monotonically_increasing_sums(
    aggregator, dd_run_check, mock_http_response
):
    counter_t0 = """
    # HELP car_counter_total The number of cars seen coming into lot
    # TYPE car_counter_total counter
    car_counter_total{make="honda", color="red"} 120
    car_counter_total{make="honda", color="green"} 95
    car_counter_total{make="honda", color="blue"} 88
    """.strip()

    counter_t1 = """
    # HELP car_counter_total The number of cars seen coming into lot
    # TYPE car_counter_total counter
    car_counter_total{make="honda", color="red"} 130
    car_counter_total{make="honda", color="green"} 100
    car_counter_total{make="honda", color="blue"} 92
    """.strip()

    check = get_check({'metrics': ['.+'], 'exclude_labels': ['color'], 'aggregate_metrics_on_label_exclusion': True})

    mock_http_response(counter_t0)
    dd_run_check(check)

    t0_metrics = [m for m in aggregator.metrics('test.car_counter.count') if 'make:honda' in m.tags]
    assert len(t0_metrics) == 1
    assert t0_metrics[0].value == 303.0

    aggregator.reset()

    mock_http_response(counter_t1)
    dd_run_check(check)

    t1_metrics = [m for m in aggregator.metrics('test.car_counter.count') if 'make:honda' in m.tags]
    assert len(t1_metrics) == 1
    assert t1_metrics[0].value == 322.0


@pytest.mark.parametrize(
    'payload, expected_metrics',
    [
        pytest.param(
            SUMMARY_PAYLOAD,
            [
                ('test.rpc_duration.quantile', 100, 'GAUGE', ['handler:api', 'color:red', 'quantile:0.5']),
                ('test.rpc_duration.quantile', 80, 'GAUGE', ['handler:api', 'color:blue', 'quantile:0.5']),
                ('test.rpc_duration.quantile', 500, 'GAUGE', ['handler:api', 'color:red', 'quantile:0.99']),
                ('test.rpc_duration.quantile', 400, 'GAUGE', ['handler:api', 'color:blue', 'quantile:0.99']),
                ('test.rpc_duration.sum', 5000, 'MONOTONIC_COUNT', ['handler:api', 'color:red']),
                ('test.rpc_duration.sum', 3000, 'MONOTONIC_COUNT', ['handler:api', 'color:blue']),
                ('test.rpc_duration.count', 50, 'MONOTONIC_COUNT', ['handler:api', 'color:red']),
                ('test.rpc_duration.count', 30, 'MONOTONIC_COUNT', ['handler:api', 'color:blue']),
            ],
            id='summary',
        ),
        pytest.param(
            HISTOGRAM_PAYLOAD,
            [
                (
                    'test.request_duration.bucket',
                    10,
                    'MONOTONIC_COUNT',
                    ['handler:api', 'color:red', 'upper_bound:0.1'],
                ),
                (
                    'test.request_duration.bucket',
                    5,
                    'MONOTONIC_COUNT',
                    ['handler:api', 'color:blue', 'upper_bound:0.1'],
                ),
                (
                    'test.request_duration.bucket',
                    20,
                    'MONOTONIC_COUNT',
                    ['handler:api', 'color:red', 'upper_bound:1.0'],
                ),
                (
                    'test.request_duration.bucket',
                    12,
                    'MONOTONIC_COUNT',
                    ['handler:api', 'color:blue', 'upper_bound:1.0'],
                ),
                ('test.request_duration.sum', 100.5, 'MONOTONIC_COUNT', ['handler:api', 'color:red']),
                ('test.request_duration.sum', 50.3, 'MONOTONIC_COUNT', ['handler:api', 'color:blue']),
                ('test.request_duration.count', 25, 'MONOTONIC_COUNT', ['handler:api', 'color:red']),
                ('test.request_duration.count', 15, 'MONOTONIC_COUNT', ['handler:api', 'color:blue']),
            ],
            id='histogram',
        ),
    ],
)
def test_non_aggregable_types_given_exclude_labels_preserves_all_labels(
    aggregator, dd_run_check, mock_http_response, payload, expected_metrics
):
    mock_http_response(payload)
    check = get_check({'metrics': ['.+'], 'exclude_labels': ['color'], 'aggregate_metrics_on_label_exclusion': True})
    dd_run_check(check)

    for name, value, metric_type, extra_tags in expected_metrics:
        aggregator.assert_metric(
            name,
            value,
            metric_type=getattr(aggregator, metric_type),
            tags=['endpoint:test'] + extra_tags,
        )

    aggregator.assert_all_metrics_covered()


def test_gauge_given_type_override_to_rate_skips_aggregation(aggregator, dd_run_check, mock_http_response):
    mock_http_response(GAUGE_PAYLOAD)
    check = get_check(
        {
            'metrics': [{'.+': {'type': 'rate'}}],
            'exclude_labels': ['color'],
            'aggregate_metrics_on_label_exclusion': True,
        }
    )
    dd_run_check(check)

    all_metrics = aggregator.metrics('test.cars_in_lot')
    honda_civic = [
        m
        for m in all_metrics
        if 'make:honda' in m.tags and 'model:civic' in m.tags and not any(t.startswith('license:') for t in m.tags)
    ]
    assert len(honda_civic) == 3

    for m in all_metrics:
        assert not any(t.startswith('color:') for t in m.tags)


def test_gauge_given_include_and_exclude_labels_with_aggregation(aggregator, dd_run_check, mock_http_response):
    mock_http_response(GAUGE_PAYLOAD)
    check = get_check(
        {
            'metrics': ['.+'],
            'exclude_labels': ['color'],
            'include_labels': ['make', 'color'],
            'aggregate_metrics_on_label_exclusion': True,
        }
    )
    dd_run_check(check)

    # color excluded, include_labels restricts to make only (model and license dropped)
    # honda: 5+3+4 (color variants) + 5+6 (license variants) = 23
    # toyota: 2+3+1 = 6
    aggregator.assert_metric(
        'test.cars_in_lot',
        23.0,
        metric_type=aggregator.GAUGE,
        tags=['endpoint:test', 'make:honda'],
    )
    aggregator.assert_metric(
        'test.cars_in_lot',
        6.0,
        metric_type=aggregator.GAUGE,
        tags=['endpoint:test', 'make:toyota'],
    )

    aggregator.assert_all_metrics_covered()
