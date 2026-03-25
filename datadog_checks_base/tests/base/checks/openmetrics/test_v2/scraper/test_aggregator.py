# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
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
    check = get_check({'metrics': ['.+'], 'exclude_labels': ['color']})
    dd_run_check(check)

    all_metrics = aggregator.metrics('test.cars_in_lot')

    # Samples with the excluded color label are summed and color tag is absent
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

    # Samples without the excluded label are collected individually
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
    # license tag is preserved since it was not excluded
    license_metrics = [m for m in all_metrics if any(t.startswith('license:') for t in m.tags)]
    assert len(license_metrics) == 2

    aggregator.assert_all_metrics_covered()


def test_counter_given_exclude_labels_submits_summed_value(aggregator, dd_run_check, mock_http_response):
    mock_http_response(COUNTER_PAYLOAD)
    check = get_check({'metrics': ['.+'], 'exclude_labels': ['color']})
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
    # Verify summed counter values increase monotonically across scrapes.
    # t0: red=120, green=95, blue=88 → sum=303
    # t1: red=130, green=100, blue=92 → sum=322
    # Agent computes delta: 322 - 303 = 19 = (10 + 5 + 4)
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

    check = get_check({'metrics': ['.+'], 'exclude_labels': ['color']})

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

    # The agent computes the delta: 322 - 303 = 19
    # This equals sum of individual deltas: (10 + 5 + 4) = 19
    assert t1_metrics[0].value - t0_metrics[0].value == 19.0


def test_summary_given_exclude_labels_ignores_exclusion(aggregator, dd_run_check, mock_http_response):
    # Summary metrics skip label exclusion entirely to preserve unique contexts
    mock_http_response(SUMMARY_PAYLOAD)
    check = get_check({'metrics': ['.+'], 'exclude_labels': ['color']})
    dd_run_check(check)

    # color tag is preserved — each color variant remains a separate context
    aggregator.assert_metric(
        'test.rpc_duration.sum',
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'handler:api', 'color:red'],
    )
    aggregator.assert_metric(
        'test.rpc_duration.sum',
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'handler:api', 'color:blue'],
    )
    aggregator.assert_metric(
        'test.rpc_duration.quantile',
        metric_type=aggregator.GAUGE,
        tags=['endpoint:test', 'handler:api', 'color:red', 'quantile:0.5'],
    )
    aggregator.assert_metric(
        'test.rpc_duration.quantile',
        metric_type=aggregator.GAUGE,
        tags=['endpoint:test', 'handler:api', 'color:blue', 'quantile:0.99'],
    )

    for m in aggregator.metrics('test.rpc_duration.sum'):
        assert any(t.startswith('color:') for t in m.tags), f"Expected 'color' tag preserved in {m.tags}"


def test_histogram_given_exclude_labels_ignores_exclusion(aggregator, dd_run_check, mock_http_response):
    # Histogram metrics skip label exclusion entirely to preserve unique contexts
    mock_http_response(HISTOGRAM_PAYLOAD)
    check = get_check({'metrics': ['.+'], 'exclude_labels': ['color']})
    dd_run_check(check)

    # color tag is preserved — each color variant remains a separate context
    aggregator.assert_metric(
        'test.request_duration.count',
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'handler:api', 'color:red'],
    )
    aggregator.assert_metric(
        'test.request_duration.count',
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'handler:api', 'color:blue'],
    )
    aggregator.assert_metric(
        'test.request_duration.sum',
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'handler:api', 'color:red'],
    )

    for name in ('test.request_duration.count', 'test.request_duration.sum', 'test.request_duration.bucket'):
        for m in aggregator.metrics(name):
            assert any(t.startswith('color:') for t in m.tags), f"Expected 'color' tag preserved in {m.tags}"
