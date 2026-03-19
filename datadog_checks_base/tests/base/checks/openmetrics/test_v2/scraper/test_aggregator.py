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


def test_gauge_given_exclude_labels_returns_summed_values(aggregator, dd_run_check, mock_http_response):
    mock_http_response(GAUGE_PAYLOAD)
    check = get_check({'metrics': ['.+'], 'exclude_labels': ['color']})
    dd_run_check(check)

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
    aggregator.assert_all_metrics_covered()


def test_gauge_given_no_exclude_labels_returns_individual_values(aggregator, dd_run_check, mock_http_response):
    mock_http_response(GAUGE_PAYLOAD)
    check = get_check({'metrics': ['.+']})
    dd_run_check(check)

    aggregator.assert_metric(
        'test.cars_in_lot',
        5.0,
        tags=['endpoint:test', 'make:honda', 'model:civic', 'color:#FF5733'],
    )
    aggregator.assert_metric(
        'test.cars_in_lot',
        3.0,
        tags=['endpoint:test', 'make:honda', 'model:civic', 'color:#4CAF50'],
    )


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


def test_counter_given_exclude_labels_submits_monotonically_increasing_sums(
    aggregator, dd_run_check, mock_http_response
):
    """Verify that summed counter values increase monotonically across scrapes,
    enabling the agent aggregator to compute correct deltas.

    Scrape t0: red=120, green=95, blue=88  → submitted sum=303
    Scrape t1: red=130, green=100, blue=92 → submitted sum=322

    The agent (Go side) computes 322 - 303 = 19, which equals the sum of
    individual deltas: (130-120) + (100-95) + (92-88) = 10 + 5 + 4 = 19.
    """
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
    honda_tags = ['endpoint:test', 'make:honda']

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


def test_gauge_given_exclude_labels_not_present_in_metric_returns_individual_values(
    aggregator, dd_run_check, mock_http_response
):
    """When the excluded label doesn't exist on a metric, no collisions occur
    and each sample is submitted individually — no aggregation."""
    payload = """
    # HELP temperature Current temperature reading
    # TYPE temperature gauge
    temperature{sensor="kitchen"} 22.5
    temperature{sensor="bedroom"} 19.0
    temperature{sensor="garage"} 15.0
    """.strip()

    mock_http_response(payload)
    check = get_check({'metrics': ['.+'], 'exclude_labels': ['color']})
    dd_run_check(check)

    aggregator.assert_metric('test.temperature', 22.5, tags=['endpoint:test', 'sensor:kitchen'])
    aggregator.assert_metric('test.temperature', 19.0, tags=['endpoint:test', 'sensor:bedroom'])
    aggregator.assert_metric('test.temperature', 15.0, tags=['endpoint:test', 'sensor:garage'])
    aggregator.assert_all_metrics_covered()


def test_summary_given_exclude_labels_passes_through_unchanged(aggregator, dd_run_check, mock_http_response):
    mock_http_response(SUMMARY_PAYLOAD)
    check = get_check({'metrics': ['.+'], 'exclude_labels': ['color']})
    dd_run_check(check)

    aggregator.assert_metric(
        'test.rpc_duration.sum',
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'handler:api'],
    )
    aggregator.assert_metric(
        'test.rpc_duration.count',
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'handler:api'],
    )
    aggregator.assert_metric(
        'test.rpc_duration.quantile',
        metric_type=aggregator.GAUGE,
        tags=['endpoint:test', 'handler:api', 'quantile:0.5'],
    )
    aggregator.assert_metric(
        'test.rpc_duration.quantile',
        metric_type=aggregator.GAUGE,
        tags=['endpoint:test', 'handler:api', 'quantile:0.99'],
    )


def test_histogram_given_exclude_labels_passes_through_unchanged(aggregator, dd_run_check, mock_http_response):
    mock_http_response(HISTOGRAM_PAYLOAD)
    check = get_check({'metrics': ['.+'], 'exclude_labels': ['color']})
    dd_run_check(check)
    dd_run_check(check)

    aggregator.assert_metric(
        'test.request_duration.count',
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'handler:api'],
    )
    aggregator.assert_metric(
        'test.request_duration.sum',
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'handler:api'],
    )
