# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Property tests for OpenMetrics replay-body mutations.

The integration-level replay PBT relies on mutating captured OpenMetrics bodies
without changing their semantic sample set. These tests prove that the helper
parser/renderer and label-order mutator preserve sample identity for generated
simple sample lines before those mutations are used against real replay caches.
"""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from datadog_checks.dev.replay.pbt.openmetrics import (
    OpenMetricsSample,
    mutate_body_label_order,
    parse_sample_line,
    render_sample,
    reorder_sample_labels,
    semantic_samples,
)

pbt_settings = settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])

metric_names = st.from_regex(r'[A-Za-z_:][A-Za-z0-9_:]{0,30}', fullmatch=True)
label_names = st.from_regex(r'[A-Za-z_][A-Za-z0-9_]{0,20}', fullmatch=True)
label_values = st.text(
    alphabet=st.characters(blacklist_categories=('Cs',), blacklist_characters=['\x00', '\n', '"', '\\', '{', '}', ',']),
    max_size=40,
)
values = st.one_of(
    st.integers(min_value=-1_000_000, max_value=1_000_000).map(str),
    st.floats(allow_nan=False, allow_infinity=False, width=32).map(lambda value: format(value, '.8g')),
)
timestamps = st.one_of(st.none(), st.integers(min_value=0, max_value=4_102_444_800).map(str))
label_sets = st.dictionaries(label_names, label_values, max_size=8).map(lambda labels: tuple(labels.items()))
samples = st.builds(OpenMetricsSample, name=metric_names, labels=label_sets, value=values, timestamp=timestamps)


@pbt_settings
@given(sample=samples)
def test_sample_render_parse_round_trips_semantics(sample):
    parsed = parse_sample_line(render_sample(sample))

    assert parsed is not None
    assert parsed.semantic_key() == sample.semantic_key()


@pbt_settings
@given(sample=samples.filter(lambda sample: len(sample.labels) >= 2))
def test_reordering_labels_preserves_sample_semantics(sample):
    original = render_sample(sample, labels=reversed(sample.labels))
    mutated = reorder_sample_labels(original)

    original_sample = parse_sample_line(original)
    mutated_sample = parse_sample_line(mutated)

    assert original_sample is not None
    assert mutated_sample is not None
    assert mutated_sample.semantic_key() == original_sample.semantic_key()


@pbt_settings
@given(prefix=st.text(max_size=40), sample=samples)
def test_body_label_order_mutation_preserves_sample_semantics(prefix, sample):
    body = '\n'.join(
        [
            '# HELP example_metric Example metric',
            prefix,
            render_sample(sample, labels=reversed(sample.labels)),
            '',
        ]
    )

    assert semantic_samples(mutate_body_label_order(body)) == semantic_samples(body)


@pbt_settings
@given(line=st.one_of(st.just(''), st.just('# HELP metric help'), st.just('# TYPE metric gauge')))
def test_label_order_mutation_preserves_non_sample_lines(line):
    assert reorder_sample_labels(line) == line
