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
