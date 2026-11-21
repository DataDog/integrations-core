# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import csv
import os

import pytest

from datadog_checks.hivemq import HivemqCheck
from datadog_checks.hivemq.metrics import COUNTER_METRICS, GAUGE_METRICS, HISTOGRAM_METRICS

from . import common

pytestmark = [pytest.mark.unit]

HISTOGRAM_SUFFIXES = (
    '50th_percentile',
    '75th_percentile',
    '95th_percentile',
    '98th_percentile',
    '99th_percentile',
    '999th_percentile',
    'count',
)


def _load_metadata_names():
    metadata_path = os.path.join(os.path.dirname(common.HERE), 'metadata.csv')
    with open(metadata_path) as f:
        return {row['metric_name'] for row in csv.DictReader(f)}


def test_metric_map_targets_exist_in_metadata():
    """
    Every name the OpenMetrics collection path can submit must already be a metric
    this integration documents (via JMX collection today), so that switching
    `use_openmetrics` never introduces a name that isn't in metadata.csv.
    """
    metadata_names = _load_metadata_names()
    missing = set()

    for target in GAUGE_METRICS.values():
        missing.add(f'hivemq.{target}') if f'hivemq.{target}' not in metadata_names else None

    for target in COUNTER_METRICS.values():
        full = f'hivemq.{target}'
        if full not in metadata_names:
            missing.add(full)

    for base in HISTOGRAM_METRICS.values():
        for suffix in HISTOGRAM_SUFFIXES:
            full = f'hivemq.{base}.{suffix}'
            if full not in metadata_names:
                missing.add(full)

    assert not missing


def test_metric_map_has_no_name_collisions():
    """
    No two entries across the gauge/counter/histogram maps may resolve to the same
    submitted metric name -- e.g. a histogram's derived `.count` must never collide
    with an unrelated counter's `.count`.
    """
    seen = {}
    collisions = []

    def register(name, source):
        if name in seen and seen[name] != source:
            collisions.append((name, seen[name], source))
        else:
            seen[name] = source

    for wire, target in GAUGE_METRICS.items():
        register(target, ('gauge', wire))

    for wire, target in COUNTER_METRICS.items():
        register(target, ('counter', wire))

    for wire, base in HISTOGRAM_METRICS.items():
        for suffix in HISTOGRAM_SUFFIXES:
            register(f'{base}.{suffix}', ('histogram', wire))

    assert not collisions


def test_check_collects_gauge_counter_and_histogram(dd_run_check, aggregator, mock_http_response):
    fixture_path = os.path.join(common.HERE, 'fixtures', 'metrics.txt')
    mock_http_response(file_path=fixture_path)

    check = HivemqCheck('hivemq', {}, [common.OPENMETRICS_INSTANCE])
    dd_run_check(check)

    aggregator.assert_metric('hivemq.system.system_cpu.load', value=0.42, metric_type=aggregator.GAUGE)
    aggregator.assert_metric(
        'hivemq.messages.incoming.publish.count', value=1234, metric_type=aggregator.MONOTONIC_COUNT
    )

    aggregator.assert_metric(
        'hivemq.messages.incoming.publish.bytes.50th_percentile', value=100.0, metric_type=aggregator.GAUGE
    )
    aggregator.assert_metric(
        'hivemq.messages.incoming.publish.bytes.999th_percentile', value=260.0, metric_type=aggregator.GAUGE
    )
    aggregator.assert_metric(
        'hivemq.messages.incoming.publish.bytes.count', value=42, metric_type=aggregator.MONOTONIC_COUNT
    )
