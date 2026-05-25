# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Integration-level replay PBT driven by `ddev env replay-pbt`.

These tests are the real integration checks for replay-PBT: they take an
adapter-saved compare-check cache, run the target integration through cached
replay, optionally mutate the cache, and assert properties over normalized check
output. The CLI command supplies the target/cache through a JSON config file
so this file remains normal pytest/Hypothesis code with reproducible artifacts.
"""

from __future__ import annotations

import csv
import json
import math
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from datadog_checks.dev.replay.pbt.cache import (
    copy_replay_cache,
    mutate_request_capture_comments_and_blank_lines,
    mutate_request_capture_final_newline,
    mutate_request_capture_help_removal,
    mutate_request_capture_help_text,
    mutate_request_capture_label_order,
)
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

PROPERTIES = (
    'deterministic',
    'openmetrics-label-order',
    'openmetrics-comments-blank-lines',
    'openmetrics-final-newline',
    'openmetrics-help-text',
    'openmetrics-help-removal',
    'metadata-emitted-metrics',
    'output-finite-values',
    'rate-finite-values',
    'monotonic-count-nonnegative',
)


class ReplayPBTContext:
    def __init__(self, config: dict) -> None:
        self.integration = config['integration']
        self.environment = config['environment']
        self.cache = Path(config['replay_cache'])
        self.target_ref = config.get('target_ref') or config.get('ref') or 'HEAD'
        self.fixture_ref = config.get('fixture_ref') or self.target_ref
        self.properties = set(config.get('properties') or PROPERTIES)
        self.artifacts = Path(config['artifacts'])
        self.repo = Path(config.get('repo') or Path(__file__).resolve().parents[4])
        self.readings = config.get('readings') or 1
        self.check_class = config.get('check_class')
        self.adapters = config.get('adapters') or 'all'
        self.record_env = config.get('record_env') or config.get('old_env')
        self.replay_env = config.get('replay_env') or config.get('new_env')


@pytest.fixture(scope='session')
def replay_pbt_context(pytestconfig) -> ReplayPBTContext:
    config_path = os.environ.get('DDEV_REPLAY_PBT_CONFIG') or pytestconfig.getoption(
        '--replay-pbt-config', default=None
    )
    if not config_path:
        pytest.skip('Pass --replay-pbt-config or run through `ddev env replay-pbt`.')
    return ReplayPBTContext(json.loads(Path(config_path).read_text()))


def _skip_unselected(context: ReplayPBTContext, property_name: str) -> None:
    if property_name not in context.properties:
        pytest.skip(f'{property_name} was not selected for this replay-pbt run.')


def _run_compare_check_cache(
    *,
    context: ReplayPBTContext,
    cache: Path | str,
    artifacts: Path,
) -> dict:
    ddev_executable = Path(sys.executable).with_name('ddev')
    command = [
        str(ddev_executable),
        '--no-interactive',
        'env',
        'compare-check',
        context.integration,
        context.environment,
        '--record-ref',
        context.fixture_ref,
        '--replay-ref',
        context.target_ref,
        '--replay-cache',
        str(cache),
        '--artifacts',
        str(artifacts),
        '--exact-artifacts-dir',
        '--overwrite',
        '--readings',
        str(context.readings),
        '--adapters',
        context.adapters,
    ]
    if context.check_class:
        command.extend(['--check-class', context.check_class])
    if context.record_env:
        command.extend(['--record-env', context.record_env])
    if context.replay_env:
        command.extend(['--replay-env', context.replay_env])

    result = subprocess.run(command, cwd=Path.cwd(), text=True, capture_output=True)
    assert result.returncode == 0, f'stdout:\n{result.stdout}\nstderr:\n{result.stderr}'
    return json.loads((artifacts / 'diff.json').read_text())


def _read_normalized(run_dir: Path) -> dict:
    return json.loads((run_dir / 'replay.normalized.json').read_text())


RATE = 1
MONOTONIC_COUNT = 3


def _assert_normalized_output_contract(output: dict[str, Any]) -> None:
    for collection in ('metrics', 'service_checks'):
        assert isinstance(output.get(collection), list), f'{collection} must be a list'

    for index, metric in enumerate(output.get('metrics', [])):
        assert isinstance(metric.get('name'), str) and metric['name'], f'metric[{index}] has no name'
        value = metric.get('value')
        assert isinstance(value, int | float), f'metric[{index}] value is not numeric: {value!r}'
        assert math.isfinite(value), f'metric[{index}] value is not finite: {value!r}'
        _assert_stable_tags(metric.get('tags'), f'metric[{index}]')

    for index, service_check in enumerate(output.get('service_checks', [])):
        assert isinstance(service_check.get('name'), str) and service_check['name'], (
            f'service_check[{index}] has no name'
        )
        status = service_check.get('status')
        assert status in {0, 1, 2, 3}, f'service_check[{index}] has invalid status: {status!r}'
        _assert_stable_tags(service_check.get('tags'), f'service_check[{index}]')


def _assert_stable_tags(tags: Any, owner: str) -> None:
    if tags is None:
        return
    assert isinstance(tags, list), f'{owner} tags must be a list or null'
    assert all(isinstance(tag, str) and tag for tag in tags), f'{owner} tags must be non-empty strings'
    assert tags == sorted(tags), f'{owner} tags are not sorted: {tags!r}'
    assert len(tags) == len(set(tags)), f'{owner} tags contain duplicates: {tags!r}'


def _metric_contexts(output: dict[str, Any]) -> set[tuple[Any, ...]]:
    return {
        (
            metric.get('name'),
            metric.get('type'),
            metric.get('hostname'),
            metric.get('device'),
            tuple(metric.get('tags') or []),
        )
        for metric in output.get('metrics', [])
    }


def _service_check_contexts(output: dict[str, Any]) -> set[tuple[Any, ...]]:
    return {
        (
            service_check.get('name'),
            service_check.get('status'),
            service_check.get('hostname'),
            tuple(service_check.get('tags') or []),
        )
        for service_check in output.get('service_checks', [])
    }


def _assert_same_context_coverage(original: dict[str, Any], mutated: dict[str, Any]) -> None:
    for name, context_fn in (('metric', _metric_contexts), ('service_check', _service_check_contexts)):
        original_contexts = context_fn(original)
        mutated_contexts = context_fn(mutated)
        dropped = sorted(original_contexts - mutated_contexts, key=repr)
        added = sorted(mutated_contexts - original_contexts, key=repr)
        assert not dropped, f'{name} contexts dropped by mutation: {dropped[:10]!r}'
        assert not added, f'{name} contexts added by mutation: {added[:10]!r}'


def _normalized_reading_outputs(output: dict[str, Any]) -> list[dict[str, Any]]:
    if output.get('version') == 2 and isinstance(output.get('readings'), list):
        return [reading.get('output', {}) for reading in output['readings']]
    return [output]


def _assert_normalized_outputs_match(original: dict[str, Any], mutated: dict[str, Any]) -> None:
    original_readings = _normalized_reading_outputs(original)
    mutated_readings = _normalized_reading_outputs(mutated)
    assert len(original_readings) == len(mutated_readings), (
        f'reading count changed: {len(original_readings)} != {len(mutated_readings)}'
    )
    for index, (original_output, mutated_output) in enumerate(zip(original_readings, mutated_readings, strict=True)):
        _assert_normalized_output_contract(original_output)
        _assert_normalized_output_contract(mutated_output)
        _assert_same_context_coverage(original_output, mutated_output)
        assert original_output == mutated_output, f'normalized output differs at reading {index}'


AGGREGATOR_TYPE_NAMES = {
    0: 'gauge',
    1: 'rate',
    2: 'count',
    3: 'monotonic_count',
    4: 'counter',
    5: 'histogram',
    6: 'historate',
}

SUBMISSION_TO_METADATA_TYPE = {
    'gauge': 'gauge',
    'rate': 'gauge',
    'count': 'count',
    'monotonic_count': 'count',
    'counter': 'rate',
    'histogram': 'rate',
    'historate': 'rate',
}


def _load_metadata_rows(repo_root: Path, integration: str) -> dict[str, dict[str, str]]:
    metadata_path = repo_root / integration / 'metadata.csv'
    assert metadata_path.is_file(), f'metadata.csv not found: {metadata_path}'

    rows = {}
    with metadata_path.open(newline='') as f:
        for row in csv.DictReader(f):
            metric_name = row.get('metric_name') or ''
            assert metric_name, f'metadata row without metric_name in {metadata_path}'
            assert metric_name not in rows, f'duplicate metadata metric_name {metric_name!r} in {metadata_path}'
            rows[metric_name] = row
    return rows


def _assert_rate_values_finite(output: dict[str, Any]) -> None:
    seen = 0
    for reading_output in _normalized_reading_outputs(output):
        _assert_normalized_output_contract(reading_output)
        for index, metric in enumerate(reading_output.get('metrics', [])):
            if metric.get('type') != RATE:
                continue
            seen += 1
            value = metric.get('value')
            assert isinstance(value, int | float) and math.isfinite(value), f'rate metric[{index}] is not finite'
    if seen == 0:
        pytest.skip('No rate metrics emitted by this replay cache.')


def _assert_monotonic_count_values_nonnegative(output: dict[str, Any]) -> None:
    seen = 0
    for reading_output in _normalized_reading_outputs(output):
        _assert_normalized_output_contract(reading_output)
        for index, metric in enumerate(reading_output.get('metrics', [])):
            if metric.get('type') != MONOTONIC_COUNT:
                continue
            if str(metric.get('name', '')).endswith('.sum'):
                continue
            seen += 1
            value = metric.get('value')
            assert isinstance(value, int | float) and value >= 0, f'monotonic_count metric[{index}] is negative'
    if seen == 0:
        pytest.skip('No non-sum monotonic_count metrics emitted by this replay cache.')


def _assert_emitted_metrics_match_metadata(output: dict[str, Any], metadata_rows: dict[str, dict[str, str]]) -> None:
    missing = []
    mismatched = []
    emitted_count = 0
    for reading_output in _normalized_reading_outputs(output):
        _assert_normalized_output_contract(reading_output)
        emitted_count += len(reading_output.get('metrics', []))
        for metric in reading_output.get('metrics', []):
            name = metric.get('name')
            row = metadata_rows.get(name)
            if row is None:
                missing.append(name)
                continue

            submission_type = AGGREGATOR_TYPE_NAMES.get(metric.get('type'))
            mapped_type = SUBMISSION_TO_METADATA_TYPE.get(submission_type or '')
            expected_type = row.get('metric_type')
            if mapped_type != expected_type:
                mismatched.append(
                    {
                        'metric': name,
                        'submission_type': submission_type,
                        'mapped_type': mapped_type,
                        'metadata_type': expected_type,
                    }
                )

    assert emitted_count, 'normalized output has no emitted metrics to validate against metadata.csv'
    assert not missing, f'emitted metrics missing from metadata.csv: {sorted(set(missing))[:20]!r}'
    assert not mismatched, f'emitted metric type mismatches against metadata.csv: {mismatched[:20]!r}'


def test_normalized_output_contract_accepts_minimal_output():
    _assert_normalized_output_contract(
        {
            'metrics': [{'name': 'example.metric', 'type': 0, 'value': 1.0, 'tags': ['a:1', 'b:2']}],
            'service_checks': [{'name': 'example.check', 'status': 0, 'tags': ['a:1']}],
        }
    )


def test_normalized_output_contract_rejects_unstable_tags():
    with pytest.raises(AssertionError, match='tags are not sorted'):
        _assert_normalized_output_contract(
            {
                'metrics': [{'name': 'example.metric', 'type': 0, 'value': 1.0, 'tags': ['b:2', 'a:1']}],
                'service_checks': [],
            }
        )


def test_normalized_output_contract_rejects_non_finite_metric_values():
    with pytest.raises(AssertionError, match='not finite'):
        _assert_normalized_output_contract(
            {
                'metrics': [{'name': 'example.metric', 'type': 0, 'value': float('nan'), 'tags': []}],
                'service_checks': [],
            }
        )


def test_same_context_coverage_rejects_added_metric_contexts():
    original = {'metrics': [], 'service_checks': []}
    mutated = {
        'metrics': [{'name': 'invented.metric', 'type': 0, 'value': 1.0, 'tags': []}],
        'service_checks': [],
    }

    with pytest.raises(AssertionError, match='contexts added'):
        _assert_normalized_outputs_match(original, mutated)


def test_emitted_metrics_match_metadata_accepts_mapped_submission_types():
    output = {
        'metrics': [
            {'name': 'example.gauge', 'type': 0, 'value': 1.0, 'tags': []},
            {'name': 'example.count', 'type': 3, 'value': 2.0, 'tags': []},
            {'name': 'example.rate', 'type': 4, 'value': 3.0, 'tags': []},
        ],
        'service_checks': [],
    }
    metadata_rows = {
        'example.gauge': {'metric_type': 'gauge'},
        'example.count': {'metric_type': 'count'},
        'example.rate': {'metric_type': 'rate'},
    }

    _assert_emitted_metrics_match_metadata(output, metadata_rows)


def test_emitted_metrics_match_metadata_rejects_missing_metric():
    output = {'metrics': [{'name': 'missing.metric', 'type': 0, 'value': 1.0, 'tags': []}], 'service_checks': []}

    with pytest.raises(AssertionError, match='missing from metadata'):
        _assert_emitted_metrics_match_metadata(output, {})


def test_emitted_metrics_match_metadata_rejects_type_mismatch():
    output = {'metrics': [{'name': 'example.metric', 'type': 0, 'value': 1.0, 'tags': []}], 'service_checks': []}
    metadata_rows = {'example.metric': {'metric_type': 'count'}}

    with pytest.raises(AssertionError, match='type mismatches'):
        _assert_emitted_metrics_match_metadata(output, metadata_rows)


def test_rate_values_finite_rejects_non_finite_rate():
    output = {
        'metrics': [{'name': 'example.rate', 'type': RATE, 'value': float('inf'), 'tags': []}],
        'service_checks': [],
    }

    with pytest.raises(AssertionError, match='not finite'):
        _assert_rate_values_finite(output)


def test_monotonic_count_values_nonnegative_rejects_negative_count():
    output = {
        'metrics': [{'name': 'example.count', 'type': MONOTONIC_COUNT, 'value': -1.0, 'tags': []}],
        'service_checks': [],
    }

    with pytest.raises(AssertionError, match='negative'):
        _assert_monotonic_count_values_nonnegative(output)


def test_cached_replay_is_deterministic_for_same_ref(replay_pbt_context: ReplayPBTContext):
    # Determinism property: replaying the same cached fixture through the same
    # integration ref twice should produce identical normalized output. The
    # first compare-check run also materializes `auto`/`latest` caches into an
    # exact artifact directory; the second run replays that materialized cache so
    # this catches nondeterminism in check execution, replay adapters,
    # normalization, and compare-check artifact regeneration.
    property_name = 'deterministic'
    _skip_unselected(replay_pbt_context, property_name)

    first = replay_pbt_context.artifacts / property_name / 'first'
    second = replay_pbt_context.artifacts / property_name / 'second'
    first_diff = _run_compare_check_cache(context=replay_pbt_context, cache=replay_pbt_context.cache, artifacts=first)
    second_diff = _run_compare_check_cache(context=replay_pbt_context, cache=first, artifacts=second)

    assert first_diff['changed'] is False
    assert second_diff['changed'] is False
    _assert_normalized_outputs_match(_read_normalized(first), _read_normalized(second))


@settings(max_examples=1, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(mutation=st.sampled_from(['sort-openmetrics-labels']))
def test_label_order_mutated_cache_matches_original_output(replay_pbt_context: ReplayPBTContext, mutation: str):
    # Metamorphic OpenMetrics property: label order in a Prometheus/OpenMetrics
    # sample is not semantically meaningful, so sorting labels inside captured
    # request bodies should not change normalized Datadog check output. This
    # test copies the replay cache, applies that mutation to adapter-saved
    # request fixtures, then runs the real integration check against original and
    # mutated caches and compares normalized outputs.
    property_name = 'openmetrics-label-order'
    _skip_unselected(replay_pbt_context, property_name)
    assert mutation == 'sort-openmetrics-labels'

    _assert_mutated_cache_matches_original_output(
        context=replay_pbt_context,
        property_name=property_name,
        mutate_cache=mutate_request_capture_label_order,
        no_change_reason='Replay cache has no request records with reorderable OpenMetrics labels.',
    )


@settings(max_examples=1, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(mutation=st.sampled_from(['insert-openmetrics-comments-and-blank-lines']))
def test_comment_and_blank_line_mutated_cache_matches_original_output(
    replay_pbt_context: ReplayPBTContext, mutation: str
):
    # Metamorphic Prometheus text property: comments and blank lines do not
    # produce metric samples, so inserting them into captured request bodies
    # should not change normalized Datadog check output. Strict OpenMetrics
    # content-type records are skipped by the cache mutator.
    property_name = 'openmetrics-comments-blank-lines'
    _skip_unselected(replay_pbt_context, property_name)
    assert mutation == 'insert-openmetrics-comments-and-blank-lines'

    _assert_mutated_cache_matches_original_output(
        context=replay_pbt_context,
        property_name=property_name,
        mutate_cache=mutate_request_capture_comments_and_blank_lines,
        no_change_reason='Replay cache has no request records with OpenMetrics samples.',
    )


@settings(max_examples=1, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(mutation=st.sampled_from(['toggle-openmetrics-final-newline']))
def test_final_newline_mutated_cache_matches_original_output(replay_pbt_context: ReplayPBTContext, mutation: str):
    # Metamorphic Prometheus text property: a single final newline difference in
    # text exposition does not produce or remove metric samples, so toggling it
    # should not change normalized Datadog check output. Strict OpenMetrics
    # content-type records are skipped by the cache mutator.
    property_name = 'openmetrics-final-newline'
    _skip_unselected(replay_pbt_context, property_name)
    assert mutation == 'toggle-openmetrics-final-newline'

    _assert_mutated_cache_matches_original_output(
        context=replay_pbt_context,
        property_name=property_name,
        mutate_cache=mutate_request_capture_final_newline,
        no_change_reason='Replay cache has no request records with OpenMetrics samples.',
    )


@settings(max_examples=1, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(mutation=st.sampled_from(['replace-openmetrics-help-text']))
def test_help_text_mutated_cache_matches_original_output(replay_pbt_context: ReplayPBTContext, mutation: str):
    # Metamorphic OpenMetrics property: HELP doc text is parser metadata and is
    # not used by Datadog metric transformation, so replacing only the doc text
    # while preserving metric names and line positions should not change output.
    property_name = 'openmetrics-help-text'
    _skip_unselected(replay_pbt_context, property_name)
    assert mutation == 'replace-openmetrics-help-text'

    _assert_mutated_cache_matches_original_output(
        context=replay_pbt_context,
        property_name=property_name,
        mutate_cache=mutate_request_capture_help_text,
        no_change_reason='Replay cache has no request records with OpenMetrics HELP text and samples.',
    )


@settings(max_examples=1, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(mutation=st.sampled_from(['remove-openmetrics-help-lines']))
def test_help_removal_mutated_cache_matches_original_output(replay_pbt_context: ReplayPBTContext, mutation: str):
    # Metamorphic OpenMetrics property: HELP text is optional parser metadata
    # and is not used by Datadog metric transformation, so removing HELP lines
    # should not change normalized Datadog check output.
    property_name = 'openmetrics-help-removal'
    _skip_unselected(replay_pbt_context, property_name)
    assert mutation == 'remove-openmetrics-help-lines'

    _assert_mutated_cache_matches_original_output(
        context=replay_pbt_context,
        property_name=property_name,
        mutate_cache=mutate_request_capture_help_removal,
        no_change_reason='Replay cache has no request records with OpenMetrics HELP text and samples.',
    )


@settings(max_examples=1, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(validation=st.sampled_from(['emitted-metrics-match-metadata']))
def test_emitted_metrics_match_metadata(replay_pbt_context: ReplayPBTContext, validation: str):
    # Metadata-backed property: metadata.csv is the canonical metric contract, so
    # every emitted metric should have a row with a compatible backend metric type.
    property_name = 'metadata-emitted-metrics'
    _skip_unselected(replay_pbt_context, property_name)
    assert validation == 'emitted-metrics-match-metadata'

    property_dir = replay_pbt_context.artifacts / property_name
    diff = _run_compare_check_cache(context=replay_pbt_context, cache=replay_pbt_context.cache, artifacts=property_dir)
    assert diff['changed'] is False
    metadata_rows = _load_metadata_rows(replay_pbt_context.repo, replay_pbt_context.integration)
    _assert_emitted_metrics_match_metadata(_read_normalized(property_dir), metadata_rows)


@settings(max_examples=1, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(validation=st.sampled_from(['finite-values']))
def test_output_values_are_finite(replay_pbt_context: ReplayPBTContext, validation: str):
    property_name = 'output-finite-values'
    _skip_unselected(replay_pbt_context, property_name)
    assert validation == 'finite-values'

    property_dir = replay_pbt_context.artifacts / property_name
    diff = _run_compare_check_cache(context=replay_pbt_context, cache=replay_pbt_context.cache, artifacts=property_dir)
    assert diff['changed'] is False
    for output in _normalized_reading_outputs(_read_normalized(property_dir)):
        _assert_normalized_output_contract(output)


@settings(max_examples=1, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(validation=st.sampled_from(['rate-values-finite']))
def test_rate_values_are_finite(replay_pbt_context: ReplayPBTContext, validation: str):
    property_name = 'rate-finite-values'
    _skip_unselected(replay_pbt_context, property_name)
    assert validation == 'rate-values-finite'

    property_dir = replay_pbt_context.artifacts / property_name
    diff = _run_compare_check_cache(context=replay_pbt_context, cache=replay_pbt_context.cache, artifacts=property_dir)
    assert diff['changed'] is False
    _assert_rate_values_finite(_read_normalized(property_dir))


@settings(max_examples=1, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(validation=st.sampled_from(['monotonic-count-nonnegative']))
def test_monotonic_count_values_are_nonnegative(replay_pbt_context: ReplayPBTContext, validation: str):
    property_name = 'monotonic-count-nonnegative'
    _skip_unselected(replay_pbt_context, property_name)
    assert validation == 'monotonic-count-nonnegative'

    property_dir = replay_pbt_context.artifacts / property_name
    diff = _run_compare_check_cache(context=replay_pbt_context, cache=replay_pbt_context.cache, artifacts=property_dir)
    assert diff['changed'] is False
    _assert_monotonic_count_values_nonnegative(_read_normalized(property_dir))


def _assert_mutated_cache_matches_original_output(
    *,
    context: ReplayPBTContext,
    property_name: str,
    mutate_cache: Callable[[Path], int],
    no_change_reason: str,
) -> None:
    property_dir = context.artifacts / property_name
    original = property_dir / 'original'
    mutated = property_dir / 'mutated'
    mutated_cache = copy_replay_cache(context.cache, property_dir / 'mutated-cache')
    changed_records = mutate_cache(mutated_cache)
    if changed_records == 0:
        pytest.skip(no_change_reason)

    original_diff = _run_compare_check_cache(context=context, cache=context.cache, artifacts=original)
    mutated_diff = _run_compare_check_cache(context=context, cache=mutated_cache, artifacts=mutated)

    assert original_diff['changed'] is False
    assert mutated_diff['changed'] is False
    _assert_normalized_outputs_match(_read_normalized(original), _read_normalized(mutated))
