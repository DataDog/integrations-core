# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.istio.metrics import NON_CONFORMING_METRICS, construct_metrics_config


def _entries_for(metrics, key):
    return [next(iter(cfg.values())) for cfg in metrics if key in cfg]


def test_pair_uses_native_dynamic_and_drops_total_entry():
    metrics = construct_metrics_config(
        {
            'go_memstats_alloc_bytes': 'go.memstats.alloc_bytes',
            'go_memstats_alloc_bytes_total': 'go.memstats.alloc_bytes_total',
        }
    )

    assert metrics == [{'go_memstats_alloc_bytes': {'name': 'go.memstats.alloc_bytes', 'type': 'native_dynamic'}}]


def test_lone_total_is_stripped_and_has_no_explicit_type():
    metrics = construct_metrics_config({'foo_bar_total': 'foo.bar_total'})

    assert metrics == [{'foo_bar': {'name': 'foo.bar'}}]


def test_non_total_only_metric_is_passed_through():
    metrics = construct_metrics_config({'foo_bar': 'foo.bar'})

    assert metrics == [{'foo_bar': {'name': 'foo.bar'}}]


def test_non_conforming_total_is_preserved():
    non_conforming = NON_CONFORMING_METRICS[0]

    metrics = construct_metrics_config({non_conforming: 'preserved.name_total'})

    assert metrics == [{non_conforming: {'name': 'preserved.name_total'}}]


def test_pair_where_total_is_non_conforming_is_not_dynamic():
    non_conforming = NON_CONFORMING_METRICS[0]
    base = non_conforming[:-6]

    metrics = construct_metrics_config(
        {
            base: 'base.name',
            non_conforming: 'base.name_total',
        }
    )

    base_entries = _entries_for(metrics, base)
    total_entries = _entries_for(metrics, non_conforming)
    assert base_entries == [{'name': 'base.name'}]
    assert total_entries == [{'name': 'base.name_total'}]


def test_multiple_pairs_are_each_dynamic():
    metrics = construct_metrics_config(
        {
            'a': 'a',
            'a_total': 'a_total',
            'b': 'b',
            'b_total': 'b_total',
        }
    )

    assert {'a': {'name': 'a', 'type': 'native_dynamic'}} in metrics
    assert {'b': {'name': 'b', 'type': 'native_dynamic'}} in metrics
    assert not any('a_total' in cfg or 'b_total' in cfg for cfg in metrics)
