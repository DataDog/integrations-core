# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import math

import pytest

from .common import ZERO_BUCKETS_URL

NAMESPACE = 'zero_buckets'

# Sketch values are approximate (DDSketch relative accuracy is about 1%)
TOLERANCE = 1.02

INSTANCE = {
    'openmetrics_endpoint': ZERO_BUCKETS_URL,
    'namespace': NAMESPACE,
    'metrics': ['zero_bucket_seconds', 'zero_bucket_large_seconds', 'negative_bucket_seconds'],
    'histogram_buckets_as_distributions': True,
    # The payload's process_start_time_seconds is in the future, so the first scrape
    # submits the full bucket counts instead of only recording them as a baseline.
    'use_process_start_time': True,
}


def get_sketch(aggregator, name, lower_bound, upper_bound):
    name = '{}.{}'.format(NAMESPACE, name)
    tags = {'lower_bound:{}'.format(lower_bound), 'upper_bound:{}'.format(upper_bound)}
    matches = [sketch for sketch in aggregator.sketches(name) if tags <= set(sketch.tags)]
    assert len(matches) == 1, 'expected one {} sketch with tags {}, got: {}'.format(
        name, sorted(tags), aggregator.sketches(name)
    )
    return matches[0]


@pytest.mark.e2e
@pytest.mark.parametrize('collect_counters', [False, True], ids=['distributions', 'distributions_with_counters'])
def test_e2e_zero_bound_histogram_buckets(dd_agent_check, collect_counters):
    # The histograms go through the Agent's aggregator and sketch interpolation; the
    # check fails if the Agent reports errors or cannot produce its JSON output.
    # The Agent only flushes sketches from earlier seconds, so the check runs twice.
    aggregator = dd_agent_check(dict(INSTANCE, collect_counters_with_distributions=collect_counters), rate=True)

    sketches = [sketch for name in aggregator.sketch_names for sketch in aggregator.sketches(name)]
    assert sketches, 'the Agent produced no sketches'
    for sketch in sketches:
        assert sketch.count > 0, sketch
        assert all(math.isfinite(value) for value in (sketch.min, sketch.max, sketch.sum, sketch.avg)), sketch
        assert not any(tag.endswith('inf') for tag in sketch.tags if 'bound:' in tag), sketch

    # Observations in the le="0" bucket are kept as a point mass at zero
    for name, count in (('zero_bucket_seconds', 7), ('zero_bucket_large_seconds', 65600)):
        sketch = get_sketch(aggregator, name, '0', '0')
        assert (sketch.count, sketch.min, sketch.max, sketch.sum, sketch.avg) == (count, 0, 0, 0, 0)

    # Buckets above zero are unchanged
    for name in ('zero_bucket_seconds', 'negative_bucket_seconds'):
        sketch = get_sketch(aggregator, name, '0', '5.0')
        assert sketch.count == 3
        assert 0 <= sketch.min <= sketch.max <= 5 * TOLERANCE

    # Explicit negative thresholds keep their (previous, 0] bucket
    sketch = get_sketch(aggregator, 'negative_bucket_seconds', '-5.0', '0')
    assert sketch.count == 2
    assert -5 * TOLERANCE <= sketch.min <= sketch.max <= 0

    if collect_counters:
        aggregator.assert_metric('{}.zero_bucket_seconds.count'.format(NAMESPACE), value=10)
        aggregator.assert_metric('{}.zero_bucket_large_seconds.count'.format(NAMESPACE), value=65600)
