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
    expand_sample_whitespace,
    insert_comment_and_blank_lines,
    mutate_body_label_order,
    mutate_help_text,
    parse_sample_line,
    remove_help_lines,
    render_sample,
    reorder_sample_labels,
    semantic_samples,
    toggle_final_newline,
    toggle_line_endings,
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


@pbt_settings
@given(sample=samples)
def test_comment_and_blank_line_insertion_preserves_sample_semantics(sample):
    body = '\n'.join(
        [
            '# HELP example_metric Example metric',
            '# TYPE example_metric gauge',
            render_sample(sample),
        ]
    )

    assert semantic_samples(insert_comment_and_blank_lines(body)) == semantic_samples(body)


@pbt_settings
@given(body=st.text(max_size=80).filter(lambda body: not semantic_samples(body)))
def test_comment_and_blank_line_insertion_preserves_non_sample_bodies(body):
    assert insert_comment_and_blank_lines(body) == body


@pbt_settings
@given(sample=samples)
def test_final_newline_toggle_preserves_sample_semantics(sample):
    body = render_sample(sample)

    assert semantic_samples(toggle_final_newline(body)) == semantic_samples(body)
    assert semantic_samples(toggle_final_newline(f'{body}\n')) == semantic_samples(body)


@pbt_settings
@given(body=st.text(max_size=80).filter(lambda body: not semantic_samples(body)))
def test_final_newline_toggle_preserves_non_sample_bodies(body):
    assert toggle_final_newline(body) == body


@pbt_settings
@given(sample=samples)
def test_help_text_mutation_preserves_sample_semantics(sample):
    body = '\n'.join(
        [
            f'# HELP {sample.name} original help text',
            f'# TYPE {sample.name} gauge',
            render_sample(sample),
        ]
    )

    assert semantic_samples(mutate_help_text(body)) == semantic_samples(body)


@pbt_settings
@given(body=st.text(max_size=80).filter(lambda body: not semantic_samples(body)))
def test_help_text_mutation_preserves_non_sample_bodies(body):
    assert mutate_help_text(body) == body


@pbt_settings
@given(sample=samples)
def test_help_line_removal_preserves_sample_semantics(sample):
    body = '\n'.join(
        [
            f'# HELP {sample.name} original help text',
            f'# TYPE {sample.name} gauge',
            render_sample(sample),
        ]
    )

    assert semantic_samples(remove_help_lines(body)) == semantic_samples(body)


@pbt_settings
@given(body=st.text(max_size=80).filter(lambda body: not semantic_samples(body)))
def test_help_line_removal_preserves_non_sample_bodies(body):
    assert remove_help_lines(body) == body


@pbt_settings
@given(sample=samples)
def test_line_ending_toggle_preserves_sample_semantics(sample):
    body = '\n'.join(
        [
            f'# HELP {sample.name} help text',
            f'# TYPE {sample.name} gauge',
            render_sample(sample),
        ]
    )

    assert semantic_samples(toggle_line_endings(body)) == semantic_samples(body)
    assert semantic_samples(toggle_line_endings(toggle_line_endings(body))) == semantic_samples(body)


@pbt_settings
@given(body=st.text(max_size=80).filter(lambda body: not semantic_samples(body)))
def test_line_ending_toggle_preserves_non_sample_bodies(body):
    assert toggle_line_endings(body) == body


def test_line_ending_toggle_round_trips_between_lf_and_crlf():
    body = 'metric 1\nmetric 2\n'

    crlf = toggle_line_endings(body)

    assert crlf == 'metric 1\r\nmetric 2\r\n'
    assert toggle_line_endings(crlf) == body


@pbt_settings
@given(sample=samples)
def test_sample_whitespace_toggle_preserves_sample_semantics(sample):
    body = '\n'.join(
        [
            f'# HELP {sample.name} help text',
            f'# TYPE {sample.name} gauge',
            render_sample(sample),
        ]
    )

    assert semantic_samples(expand_sample_whitespace(body)) == semantic_samples(body)
    assert semantic_samples(expand_sample_whitespace(expand_sample_whitespace(body))) == semantic_samples(body)


@pbt_settings
@given(body=st.text(max_size=80).filter(lambda body: not semantic_samples(body)))
def test_sample_whitespace_toggle_preserves_non_sample_bodies(body):
    assert expand_sample_whitespace(body) == body


def test_sample_whitespace_toggle_widens_then_collapses_single_space():
    body = 'metric{label="a"} 1'

    widened = expand_sample_whitespace(body)

    assert widened == 'metric{label="a"}  1'
    assert expand_sample_whitespace(widened) == body


def test_sample_whitespace_toggle_preserves_lines_without_separator_match():
    body = '# HELP metric help\n# TYPE metric gauge\nmetric 1\n'

    mutated = expand_sample_whitespace(body)

    assert mutated == '# HELP metric help\n# TYPE metric gauge\nmetric  1\n'
