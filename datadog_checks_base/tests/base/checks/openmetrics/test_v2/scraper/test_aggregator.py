# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from prometheus_client.samples import Sample

from datadog_checks.base.checks.openmetrics.v2.scraper.aggregator import (
    aggregate_sample_data,
    should_aggregate,
)


# --- should_aggregate ---


def test_should_aggregate_given_empty_exclude_labels_returns_false():
    assert should_aggregate(set()) is False


def test_should_aggregate_given_nonempty_exclude_labels_returns_true():
    assert should_aggregate({'color'}) is True


# --- gauge aggregation ---


def test_aggregate_gauge_given_colliding_tags_returns_summed_value():
    sample_data = [
        (Sample('cars_in_lot', {'make': 'honda'}, 5.0), ['make:honda'], ''),
        (Sample('cars_in_lot', {'make': 'honda'}, 3.0), ['make:honda'], ''),
        (Sample('cars_in_lot', {'make': 'honda'}, 4.0), ['make:honda'], ''),
    ]
    result = list(aggregate_sample_data(iter(sample_data), 'gauge'))
    assert len(result) == 1
    assert result[0][0].value == 12.0
    assert result[0][1] == ['make:honda']


def test_aggregate_gauge_given_no_collisions_returns_all_samples():
    sample_data = [
        (Sample('cars_in_lot', {'make': 'honda'}, 5.0), ['make:honda'], ''),
        (Sample('cars_in_lot', {'make': 'toyota'}, 3.0), ['make:toyota'], ''),
    ]
    result = list(aggregate_sample_data(iter(sample_data), 'gauge'))
    assert len(result) == 2
    values = {r[0].value for r in result}
    assert values == {5.0, 3.0}


# --- counter aggregation ---


def test_aggregate_counter_given_colliding_tags_returns_summed_value():
    sample_data = [
        (Sample('car_counter_total', {'make': 'honda'}, 120.0), ['make:honda'], ''),
        (Sample('car_counter_total', {'make': 'honda'}, 95.0), ['make:honda'], ''),
        (Sample('car_counter_total', {'make': 'honda'}, 88.0), ['make:honda'], ''),
    ]
    result = list(aggregate_sample_data(iter(sample_data), 'counter'))
    assert len(result) == 1
    assert result[0][0].value == 303.0


# --- histogram and summary pass through unchanged ---


def test_aggregate_histogram_given_colliding_tags_passes_through_unchanged():
    sample_data = [
        (Sample('req_bucket', {'le': '10'}, 5.0), ['le:10'], ''),
        (Sample('req_bucket', {'le': '10'}, 3.0), ['le:10'], ''),
    ]
    result = list(aggregate_sample_data(iter(sample_data), 'histogram'))
    assert len(result) == 2
    assert result[0][0].value == 5.0
    assert result[1][0].value == 3.0


def test_aggregate_summary_given_colliding_tags_passes_through_unchanged():
    sample_data = [
        (Sample('latency_sum', {}, 1000.0), [], ''),
        (Sample('latency_sum', {}, 500.0), [], ''),
    ]
    result = list(aggregate_sample_data(iter(sample_data), 'summary'))
    assert len(result) == 2


# --- hostname grouping ---


def test_aggregate_gauge_given_different_hostnames_returns_separate_groups():
    sample_data = [
        (Sample('cpu', {}, 10.0), ['app:web'], 'host-a'),
        (Sample('cpu', {}, 20.0), ['app:web'], 'host-b'),
    ]
    result = list(aggregate_sample_data(iter(sample_data), 'gauge'))
    assert len(result) == 2


# --- tag ordering ---


def test_aggregate_gauge_given_unsorted_tags_groups_correctly():
    sample_data = [
        (Sample('m', {}, 1.0), ['b:2', 'a:1'], ''),
        (Sample('m', {}, 2.0), ['a:1', 'b:2'], ''),
    ]
    result = list(aggregate_sample_data(iter(sample_data), 'gauge'))
    assert len(result) == 1
    assert result[0][0].value == 3.0


# --- unrecognized metric type passes through ---


def test_aggregate_given_unknown_metric_type_passes_through():
    sample_data = [
        (Sample('info_metric', {}, 1.0), ['app:web'], ''),
        (Sample('info_metric', {}, 1.0), ['app:web'], ''),
    ]
    result = list(aggregate_sample_data(iter(sample_data), 'info'))
    assert len(result) == 2
