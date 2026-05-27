# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Property tests for replay-cache mutation helpers.

These tests stay below the integration runner and verify that cache-level
mutations preserve the semantics they claim to preserve for both legacy list
captures and newer manifest-based captures. That keeps later integration PBT
failures focused on check behavior instead of malformed mutated cache files.
"""

from __future__ import annotations

import json
import shutil

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from datadog_checks.dev.replay.pbt.cache import (
    copy_replay_cache,
    mutate_request_capture_comments_and_blank_lines,
    mutate_request_capture_final_newline,
    mutate_request_capture_header_casing,
    mutate_request_capture_help_removal,
    mutate_request_capture_help_text,
    mutate_request_capture_json_object_key_order,
    mutate_request_capture_json_string_escapes,
    mutate_request_capture_json_whitespace,
    mutate_request_capture_label_order,
    mutate_request_capture_line_endings,
    mutate_request_capture_sample_whitespace,
)
from datadog_checks.dev.replay.pbt.openmetrics import OpenMetricsSample, render_sample, semantic_samples

pbt_settings = settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])

metric_names = st.from_regex(r'[A-Za-z_:][A-Za-z0-9_:]{0,30}', fullmatch=True)
label_names = st.from_regex(r'[A-Za-z_][A-Za-z0-9_]{0,20}', fullmatch=True)
label_values = st.text(
    alphabet=st.characters(
        blacklist_categories=('Cs', 'Cc'), blacklist_characters=['\x00', '\n', '"', '\\', '{', '}', ',']
    ),
    max_size=40,
)
values = st.integers(min_value=-1_000_000, max_value=1_000_000).map(str)
label_sets = st.dictionaries(label_names, label_values, min_size=2, max_size=8).map(
    lambda labels: tuple(labels.items())
)
samples = st.builds(OpenMetricsSample, name=metric_names, labels=label_sets, value=values)
sample_bodies = samples.map(
    lambda sample: '\n'.join(
        [
            '# HELP generated_metric Generated metric',
            '# TYPE generated_metric gauge',
            render_sample(sample, labels=sorted(sample.labels, reverse=True)),
            '',
        ]
    )
)


def _write_legacy_cache(cache_dir, body: str) -> None:
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    cache_dir.mkdir()
    (cache_dir / 'capture.json').write_text(json.dumps([{'method': 'GET', 'url': 'http://example.test', 'body': body}]))


def _write_manifest_cache(cache_dir, body: str, headers: dict[str, str] | None = None) -> None:
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    cache_dir.mkdir()
    (cache_dir / 'capture.json').write_text(
        json.dumps({'version': 1, 'adapters': ['requests'], 'files': {'requests': 'capture.requests.json'}})
    )
    (cache_dir / 'capture.requests.json').write_text(
        json.dumps([{'method': 'GET', 'url': 'http://example.test', 'body': body, 'headers': headers or {}}])
    )


@pbt_settings
@given(body=sample_bodies)
def test_mutating_legacy_request_capture_label_order_preserves_semantics(tmp_path, body):
    cache_dir = tmp_path / 'cache'
    _write_legacy_cache(cache_dir, body)

    assert mutate_request_capture_label_order(cache_dir) == 1

    records = json.loads((cache_dir / 'capture.json').read_text())
    assert semantic_samples(records[0]['body']) == semantic_samples(body)


@pbt_settings
@given(body=sample_bodies)
def test_mutating_manifest_request_capture_label_order_preserves_semantics(tmp_path, body):
    cache_dir = tmp_path / 'cache'
    _write_manifest_cache(cache_dir, body)

    assert mutate_request_capture_label_order(cache_dir) == 1

    records = json.loads((cache_dir / 'capture.requests.json').read_text())
    assert semantic_samples(records[0]['body']) == semantic_samples(body)


@pbt_settings
@given(body=sample_bodies)
def test_mutating_legacy_request_capture_comments_and_blank_lines_preserves_semantics(tmp_path, body):
    cache_dir = tmp_path / 'cache'
    _write_legacy_cache(cache_dir, body)

    assert mutate_request_capture_comments_and_blank_lines(cache_dir) == 1

    records = json.loads((cache_dir / 'capture.json').read_text())
    assert semantic_samples(records[0]['body']) == semantic_samples(body)


@pbt_settings
@given(body=sample_bodies)
def test_mutating_manifest_request_capture_comments_and_blank_lines_preserves_semantics(tmp_path, body):
    cache_dir = tmp_path / 'cache'
    _write_manifest_cache(cache_dir, body)

    assert mutate_request_capture_comments_and_blank_lines(cache_dir) == 1

    records = json.loads((cache_dir / 'capture.requests.json').read_text())
    assert semantic_samples(records[0]['body']) == semantic_samples(body)


@pbt_settings
@given(body=sample_bodies)
def test_mutating_legacy_request_capture_final_newline_preserves_semantics(tmp_path, body):
    cache_dir = tmp_path / 'cache'
    _write_legacy_cache(cache_dir, body)

    assert mutate_request_capture_final_newline(cache_dir) == 1

    records = json.loads((cache_dir / 'capture.json').read_text())
    assert semantic_samples(records[0]['body']) == semantic_samples(body)


@pbt_settings
@given(body=sample_bodies)
def test_mutating_manifest_request_capture_final_newline_preserves_semantics(tmp_path, body):
    cache_dir = tmp_path / 'cache'
    _write_manifest_cache(cache_dir, body)

    assert mutate_request_capture_final_newline(cache_dir) == 1

    records = json.loads((cache_dir / 'capture.requests.json').read_text())
    assert semantic_samples(records[0]['body']) == semantic_samples(body)


@pbt_settings
@given(body=sample_bodies)
def test_mutating_legacy_request_capture_help_text_preserves_semantics(tmp_path, body):
    cache_dir = tmp_path / 'cache'
    _write_legacy_cache(cache_dir, body)

    assert mutate_request_capture_help_text(cache_dir) == 1

    records = json.loads((cache_dir / 'capture.json').read_text())
    assert semantic_samples(records[0]['body']) == semantic_samples(body)


@pbt_settings
@given(body=sample_bodies)
def test_mutating_manifest_request_capture_help_text_preserves_semantics(tmp_path, body):
    cache_dir = tmp_path / 'cache'
    _write_manifest_cache(cache_dir, body)

    assert mutate_request_capture_help_text(cache_dir) == 1

    records = json.loads((cache_dir / 'capture.requests.json').read_text())
    assert semantic_samples(records[0]['body']) == semantic_samples(body)


@pbt_settings
@given(body=sample_bodies)
def test_mutating_legacy_request_capture_help_removal_preserves_semantics(tmp_path, body):
    cache_dir = tmp_path / 'cache'
    _write_legacy_cache(cache_dir, body)

    assert mutate_request_capture_help_removal(cache_dir) == 1

    records = json.loads((cache_dir / 'capture.json').read_text())
    assert semantic_samples(records[0]['body']) == semantic_samples(body)


@pbt_settings
@given(body=sample_bodies)
def test_mutating_manifest_request_capture_help_removal_preserves_semantics(tmp_path, body):
    cache_dir = tmp_path / 'cache'
    _write_manifest_cache(cache_dir, body)

    assert mutate_request_capture_help_removal(cache_dir) == 1

    records = json.loads((cache_dir / 'capture.requests.json').read_text())
    assert semantic_samples(records[0]['body']) == semantic_samples(body)


json_values = st.recursive(
    st.one_of(
        st.none(),
        st.booleans(),
        st.integers(min_value=-1_000_000, max_value=1_000_000),
        st.floats(allow_nan=False, allow_infinity=False, width=32),
        st.text(alphabet=st.characters(blacklist_categories=('Cs',)), max_size=40),
    ),
    lambda children: st.one_of(
        st.lists(children, max_size=8),
        st.dictionaries(
            st.text(alphabet=st.characters(blacklist_categories=('Cs',)), max_size=20), children, max_size=8
        ),
    ),
    max_leaves=30,
)


@pbt_settings
@given(value=json_values)
def test_mutating_manifest_request_capture_json_key_order_preserves_semantics(tmp_path, value):
    cache_dir = tmp_path / 'cache'
    body = json.dumps(value, ensure_ascii=False)
    _write_manifest_cache(cache_dir, body, headers={'Content-Type': 'application/json'})

    mutate_request_capture_json_object_key_order(cache_dir)

    records = json.loads((cache_dir / 'capture.requests.json').read_text())
    assert json.loads(records[0]['body']) == value


@pbt_settings
@given(value=json_values)
def test_mutating_manifest_request_capture_json_whitespace_preserves_semantics(tmp_path, value):
    cache_dir = tmp_path / 'cache'
    body = json.dumps(value, ensure_ascii=False)
    _write_manifest_cache(cache_dir, body, headers={'Content-Type': 'application/json'})

    mutate_request_capture_json_whitespace(cache_dir)

    records = json.loads((cache_dir / 'capture.requests.json').read_text())
    assert json.loads(records[0]['body']) == value


@pbt_settings
@given(value=json_values)
def test_mutating_manifest_request_capture_json_string_escapes_preserves_semantics(tmp_path, value):
    cache_dir = tmp_path / 'cache'
    body = json.dumps(value, ensure_ascii=False)
    _write_manifest_cache(cache_dir, body, headers={'Content-Type': 'application/json'})

    mutate_request_capture_json_string_escapes(cache_dir)

    records = json.loads((cache_dir / 'capture.requests.json').read_text())
    assert json.loads(records[0]['body']) == value


def test_prometheus_formatting_mutations_skip_strict_openmetrics_records(tmp_path):
    body = '# TYPE metric gauge\nmetric 1\n# EOF'
    headers = {'Content-Type': 'application/openmetrics-text; version=1.0.0'}
    cache_dir = tmp_path / 'cache'

    _write_manifest_cache(cache_dir, body, headers=headers)
    assert mutate_request_capture_comments_and_blank_lines(cache_dir) == 0
    assert json.loads((cache_dir / 'capture.requests.json').read_text())[0]['body'] == body

    _write_manifest_cache(cache_dir, body, headers=headers)
    assert mutate_request_capture_final_newline(cache_dir) == 0
    assert json.loads((cache_dir / 'capture.requests.json').read_text())[0]['body'] == body


@pbt_settings
@given(body=sample_bodies)
def test_mutating_manifest_request_capture_line_endings_preserves_semantics(tmp_path, body):
    cache_dir = tmp_path / 'cache'
    _write_manifest_cache(cache_dir, body)

    assert mutate_request_capture_line_endings(cache_dir) == 1

    records = json.loads((cache_dir / 'capture.requests.json').read_text())
    assert semantic_samples(records[0]['body']) == semantic_samples(body)


@pbt_settings
@given(body=sample_bodies)
def test_mutating_legacy_request_capture_line_endings_preserves_semantics(tmp_path, body):
    cache_dir = tmp_path / 'cache'
    _write_legacy_cache(cache_dir, body)

    assert mutate_request_capture_line_endings(cache_dir) == 1

    records = json.loads((cache_dir / 'capture.json').read_text())
    assert semantic_samples(records[0]['body']) == semantic_samples(body)


@pbt_settings
@given(body=sample_bodies)
def test_mutating_manifest_request_capture_sample_whitespace_preserves_semantics(tmp_path, body):
    cache_dir = tmp_path / 'cache'
    _write_manifest_cache(cache_dir, body)

    assert mutate_request_capture_sample_whitespace(cache_dir) == 1

    records = json.loads((cache_dir / 'capture.requests.json').read_text())
    assert semantic_samples(records[0]['body']) == semantic_samples(body)


@pbt_settings
@given(body=sample_bodies)
def test_mutating_legacy_request_capture_sample_whitespace_preserves_semantics(tmp_path, body):
    cache_dir = tmp_path / 'cache'
    _write_legacy_cache(cache_dir, body)

    assert mutate_request_capture_sample_whitespace(cache_dir) == 1

    records = json.loads((cache_dir / 'capture.json').read_text())
    assert semantic_samples(records[0]['body']) == semantic_samples(body)


def test_line_ending_and_whitespace_mutations_skip_strict_openmetrics_records(tmp_path):
    body = '# TYPE metric gauge\nmetric 1\n'
    headers = {'Content-Type': 'application/openmetrics-text; version=1.0.0'}
    cache_dir = tmp_path / 'cache'

    _write_manifest_cache(cache_dir, body, headers=headers)
    assert mutate_request_capture_line_endings(cache_dir) == 0
    assert json.loads((cache_dir / 'capture.requests.json').read_text())[0]['body'] == body

    _write_manifest_cache(cache_dir, body, headers=headers)
    assert mutate_request_capture_sample_whitespace(cache_dir) == 0
    assert json.loads((cache_dir / 'capture.requests.json').read_text())[0]['body'] == body


http_header_names = st.from_regex(r'[A-Za-z][A-Za-z0-9-]{0,20}', fullmatch=True).filter(
    lambda name: any(char.isalpha() for char in name)
)
http_header_values = st.text(
    alphabet=st.characters(blacklist_categories=('Cs', 'Cc'), blacklist_characters=['\n', '\r']),
    max_size=40,
)
http_header_dicts = st.dictionaries(http_header_names, http_header_values, min_size=1, max_size=6).filter(
    lambda headers: len({name.lower() for name in headers}) == len(headers)
)


@pbt_settings
@given(headers=http_header_dicts)
def test_mutating_request_capture_header_casing_preserves_header_values(tmp_path, headers):
    cache_dir = tmp_path / 'cache'
    body = 'metric 1\n'
    _write_manifest_cache(cache_dir, body, headers=headers)

    changed = mutate_request_capture_header_casing(cache_dir)

    records = json.loads((cache_dir / 'capture.requests.json').read_text())
    mutated_headers = records[0]['headers']

    case_insensitive_original = {name.lower(): value for name, value in headers.items()}
    case_insensitive_mutated = {name.lower(): value for name, value in mutated_headers.items()}
    assert case_insensitive_mutated == case_insensitive_original
    if changed:
        all_upper = all(name.isupper() or not any(char.isalpha() for char in name) for name in mutated_headers)
        all_lower = all(name.islower() or not any(char.isalpha() for char in name) for name in mutated_headers)
        assert all_upper or all_lower


def test_mutating_request_capture_header_casing_flips_mixed_case_headers(tmp_path):
    cache_dir = tmp_path / 'cache'
    _write_manifest_cache(cache_dir, 'metric 1\n', headers={'Content-Type': 'application/json', 'X-Custom': '1'})

    assert mutate_request_capture_header_casing(cache_dir) == 1

    records = json.loads((cache_dir / 'capture.requests.json').read_text())
    mutated_headers = records[0]['headers']
    assert set(mutated_headers) == {'content-type', 'x-custom'}
    assert mutated_headers['content-type'] == 'application/json'


def test_mutating_request_capture_header_casing_uppercases_already_lowercase_headers(tmp_path):
    cache_dir = tmp_path / 'cache'
    _write_manifest_cache(cache_dir, 'metric 1\n', headers={'content-type': 'application/json'})

    assert mutate_request_capture_header_casing(cache_dir) == 1

    records = json.loads((cache_dir / 'capture.requests.json').read_text())
    mutated_headers = records[0]['headers']
    assert set(mutated_headers) == {'CONTENT-TYPE'}


def test_mutating_request_capture_header_casing_skips_records_without_headers(tmp_path):
    cache_dir = tmp_path / 'cache'
    _write_manifest_cache(cache_dir, 'metric 1\n', headers={})

    assert mutate_request_capture_header_casing(cache_dir) == 0


def test_copy_replay_cache_replaces_destination(tmp_path):
    source = tmp_path / 'source'
    destination = tmp_path / 'destination'
    source.mkdir()
    destination.mkdir()
    (source / 'capture.json').write_text('source')
    (destination / 'stale').write_text('stale')

    copy_replay_cache(source, destination)

    assert (destination / 'capture.json').read_text() == 'source'
    assert not (destination / 'stale').exists()
