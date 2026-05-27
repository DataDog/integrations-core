# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Integration-level replay validation driven by `ddev env replay-pbt`.

These tests are the real integration checks for replay validation: they take an
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
import re
import subprocess
import sys
import warnings
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from datadog_checks.dev.replay.pbt.artifacts import write_property_result
from datadog_checks.dev.replay.pbt.cache import (
    copy_replay_cache,
    mutate_request_capture_comments_and_blank_lines,
    mutate_request_capture_final_newline,
    mutate_request_capture_help_removal,
    mutate_request_capture_help_text,
    mutate_request_capture_json_object_key_order,
    mutate_request_capture_json_string_escapes,
    mutate_request_capture_json_whitespace,
    mutate_request_capture_label_order,
)
from datadog_checks.dev.replay.pbt.openmetrics import parse_sample_line
from datadog_checks.dev.replay.pbt.properties import (
    PROPERTIES,
    property_requires_replay_cache,
    validation_family_for_property,
)
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st


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
        self.warnings_as_errors = bool(config.get('warnings_as_errors'))
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
        pytest.skip(f'{property_name} was not selected for this replay validation run.')


def _run_compare_check_cache(
    *,
    context: ReplayPBTContext,
    cache: Path | str,
    artifacts: Path,
    allow_diff: bool = False,
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
    diff_path = artifacts / 'diff.json'
    if allow_diff and diff_path.is_file():
        return json.loads(diff_path.read_text())

    assert result.returncode == 0, _format_compare_check_output(result)
    assert diff_path.is_file(), f'compare-check did not write {diff_path}\n{_format_compare_check_output(result)}'
    return json.loads(diff_path.read_text())


def _format_compare_check_output(result: subprocess.CompletedProcess[str]) -> str:
    return f'stdout:\n{result.stdout}\nstderr:\n{result.stderr}'


def _read_normalized(run_dir: Path) -> dict:
    return json.loads((run_dir / 'replay.normalized.json').read_text())


def _collection_change_counts(diff: dict) -> dict[str, dict[str, int]]:
    collections = diff.get('collections') or {}
    counts = {}
    for collection in DIFF_OUTPUT_COLLECTIONS:
        collection_diff = collections.get(collection) or {}
        added = len(collection_diff.get('added') or [])
        removed = len(collection_diff.get('removed') or [])
        if added or removed:
            counts[collection] = {'added': added, 'removed': removed}
    return counts


def _release_diff_findings(diff: dict) -> list[ReplayPBTFinding]:
    findings = []
    for collection, counts in _collection_change_counts(diff).items():
        total = counts['added'] + counts['removed']
        findings.append(
            ReplayPBTFinding(
                level='error',
                check='latest-release-diff',
                message=f'Output changed compared to the latest release for {collection}.',
                collection=collection,
                metric=f'{total} change(s): +{counts["added"]} -{counts["removed"]}',
            )
        )
    return findings


def _write_release_diff_artifacts(property_dir: Path, diff: dict, *, context: ReplayPBTContext) -> None:
    property_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        'changed': diff.get('changed'),
        'incomplete': diff.get('incomplete'),
        'record_ref': context.fixture_ref,
        'target_ref': context.target_ref,
        'collections': _collection_change_counts(diff),
    }
    (property_dir / 'release-diff-summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    findings = _release_diff_findings(diff)
    _write_findings(property_dir, findings)
    write_property_result(
        property_dir,
        property_name='latest-release-diff',
        artifacts=[
            {'kind': 'summary', 'path': 'release-diff-summary.json', 'format': 'json'},
            {'kind': 'findings', 'path': 'findings.json', 'format': 'json'},
            {'kind': 'findings-markdown', 'path': 'warnings.md', 'format': 'markdown'},
        ],
        counts={
            'errors': sum(1 for finding in findings if finding.level == 'error'),
            'warnings': sum(1 for finding in findings if finding.level == 'warning'),
        },
        validation_family=validation_family_for_property('latest-release-diff'),
        requires_replay_cache=property_requires_replay_cache('latest-release-diff'),
    )


RATE = 1
MONOTONIC_COUNT = 3
DIFF_OUTPUT_COLLECTIONS = (
    'metrics',
    'service_checks',
    'events',
    'metadata',
    'external_tags',
    'persistent_cache',
    'agent_logs',
    'telemetry',
)


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

    for index, stat in enumerate(output.get('adapter_stats', [])):
        assert isinstance(stat.get('adapter'), str) and stat['adapter'], f'adapter_stats[{index}] has no adapter'
        assert isinstance(stat.get('operation'), str) and stat['operation'], f'adapter_stats[{index}] has no operation'
        count = stat.get('count')
        assert isinstance(count, int) and count >= 0, f'adapter_stats[{index}] has invalid count: {count!r}'


def _assert_stable_tags(tags: Any, owner: str) -> None:
    if tags is None:
        return
    assert isinstance(tags, list), f'{owner} tags must be a list or null'
    assert all(isinstance(tag, str) and tag for tag in tags), f'{owner} tags must be non-empty strings'
    assert tags == sorted(tags), f'{owner} tags are not sorted: {tags!r}'
    assert len(tags) == len(set(tags)), f'{owner} tags contain duplicates: {tags!r}'


CHECK_STATE_TAG_ATTRIBUTES = ('tags', 'service_check_tags', '_non_internal_tags')


def _check_state_tag_contexts(output: dict[str, Any]) -> set[tuple[Any, ...]]:
    contexts = set()
    for state_index, state in enumerate(output.get('check_states', [])):
        check_id = (state.get('index', state_index), state.get('class'))
        for attr in CHECK_STATE_TAG_ATTRIBUTES:
            if attr not in state:
                continue
            tags = state.get(attr)
            _assert_stable_tags(tags, f'check_states[{state_index}].{attr}')
            contexts.add((*check_id, attr, tuple(tags or [])))
    return contexts


def _assert_repeated_run_tag_stability(envelope: dict[str, Any]) -> None:
    outputs = _normalized_reading_outputs(envelope)
    if len(outputs) < 2:
        pytest.skip('repeated-run-tag-stability requires --readings >= 2.')

    baseline = _check_state_tag_contexts(outputs[0])
    for index, output in enumerate(outputs):
        _assert_normalized_output_contract(output)
        current = _check_state_tag_contexts(output)
        if index == 0:
            continue
        added = sorted(current - baseline, key=repr)
        removed = sorted(baseline - current, key=repr)
        assert not added, f'check tag state grew or changed at reading {index}: {added[:10]!r}'
        assert not removed, f'check tag state was removed or changed at reading {index}: {removed[:10]!r}'


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


def _order_insensitive(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _order_insensitive(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return sorted((_order_insensitive(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True))
    return value


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
        if original_output != mutated_output:
            if _order_insensitive(original_output) == _order_insensitive(mutated_output):
                raise AssertionError(
                    f'normalized output differs only by ordering at reading {index}; '
                    'normalize/sort this output in replay normalization or in the check output'
                )
            raise AssertionError(f'normalized output differs at reading {index}')


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

CUSTOM_QUERY_METRIC_TYPES = frozenset(SUBMISSION_TO_METADATA_TYPE)

QUERY_METRIC_PATTERN = re.compile(
    r'(?<![A-Za-z0-9_.])(?:avg|sum|min|max|last|count|median|p\d+):'
    r'([A-Za-z_][A-Za-z0-9_.]*(?:\.[A-Za-z0-9_]+)*)\{'
)
QUERY_FILTER_PATTERN = re.compile(r'\{([^}]*)\}')
QUERY_GROUP_BY_PATTERN = re.compile(r'\bby\s*\{([^}]*)\}')
QUERY_TAG_FILTER_PATTERN = re.compile(r'\b([A-Za-z_][A-Za-z0-9_./-]*)\s*(?::|\s+IN\s*\()')
QUERY_TEMPLATE_VARIABLE_PATTERN = re.compile(r'\$([A-Za-z_][A-Za-z0-9_]*)')


@dataclass(frozen=True)
class AssetQuery:
    path: str
    asset_type: str
    query: str
    metric_names: tuple[str, ...]
    tag_keys: tuple[str, ...]


@dataclass(frozen=True)
class ReplayPBTFinding:
    level: str
    check: str
    message: str
    path: str | None = None
    query: str | None = None
    metric: str | None = None
    tag_key: str | None = None
    asset_type: str | None = None
    collection: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {
            'level': self.level,
            'check': self.check,
            'message': self.message,
            'path': self.path,
            'query': self.query,
            'metric': self.metric,
            'tag_key': self.tag_key,
            'asset_type': self.asset_type,
            'collection': self.collection,
        }


class ReplayPBTWarning(UserWarning):
    pass


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


def _load_metadata_rows_or_skip(repo_root: Path, integration: str) -> dict[str, dict[str, str]]:
    metadata_path = repo_root / integration / 'metadata.csv'
    if not metadata_path.is_file():
        pytest.skip(f'Integration has no metadata.csv: {metadata_path}')
    return _load_metadata_rows(repo_root, integration)


def _load_manifest_metric_prefix(repo_root: Path, integration: str) -> str | None:
    manifest_path = repo_root / integration / 'manifest.json'
    if not manifest_path.is_file():
        return None

    manifest = json.loads(manifest_path.read_text())
    metrics = manifest.get('assets', {}).get('integration', {}).get('metrics', {})
    prefix = metrics.get('prefix')
    return prefix if isinstance(prefix, str) and prefix else None


def _request_capture_files(cache_dir: Path) -> list[Path]:
    manifest_path = cache_dir / 'capture.json'
    manifest = json.loads(manifest_path.read_text())
    if isinstance(manifest, dict):
        files = manifest.get('files', {})
        requests_file = files.get('requests') if isinstance(files, dict) else None
        if requests_file:
            return [cache_dir / str(requests_file)]
        return []
    if isinstance(manifest, list):
        return [manifest_path]
    return []


def _iter_request_capture_records(cache_dir: Path) -> Iterator[dict[str, Any]]:
    for capture_file in _request_capture_files(cache_dir):
        records = json.loads(capture_file.read_text())
        if not isinstance(records, list):
            continue
        for record in records:
            if isinstance(record, dict):
                yield record


def _raw_openmetrics_family_name(sample_name: str) -> str:
    for suffix in ('_bucket', '_total', '_sum', '_count'):
        if sample_name.endswith(suffix):
            return sample_name[: -len(suffix)]
    return sample_name


def _observed_openmetrics_families(cache_dir: Path) -> set[str]:
    families = set()
    for record in _iter_request_capture_records(cache_dir):
        body = record.get('body')
        if not isinstance(body, str):
            continue
        for line in body.split('\n'):
            sample = parse_sample_line(line)
            if sample is not None:
                families.add(_raw_openmetrics_family_name(sample.name))
    return families


def _load_replay_config(cache_dir: Path) -> dict[str, Any]:
    config_path = cache_dir / 'config.json'
    if not config_path.is_file():
        return {}
    config = json.loads(config_path.read_text())
    return config if isinstance(config, dict) else {}


def _load_raw_metric_prefixes(cache_dir: Path) -> set[str]:
    config = _load_replay_config(cache_dir)
    instances = config.get('instances')
    if not isinstance(instances, list):
        return set()

    prefixes = set()
    for instance in instances:
        if not isinstance(instance, dict):
            continue
        for key in ('raw_metric_prefix', 'metrics_prefix'):
            value = instance.get(key)
            if isinstance(value, str) and value:
                prefixes.add(value)
    return prefixes


def _metric_name_stem(name: str, *, prefixes: set[str]) -> str:
    stem = name
    for prefix in sorted(prefixes, key=len, reverse=True):
        if stem.startswith(prefix):
            stem = stem[len(prefix) :]
            break
    for suffix in ('_bucket', '_total', '_sum', '_count', '.bucket', '.total', '.sum', '.count'):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return stem.strip('._').replace(':', '.').replace('_', '.')


def _family_is_heuristically_emitted(raw_family: str, emitted_metric_names: set[str], *, prefixes: set[str]) -> bool:
    raw_stems = {
        _metric_name_stem(raw_family, prefixes=prefixes),
        _metric_name_stem(raw_family, prefixes=set()),
    }
    raw_stems = {stem for stem in raw_stems if stem}
    for emitted_name in emitted_metric_names:
        emitted_stem = _metric_name_stem(emitted_name, prefixes=prefixes)
        for raw_stem in raw_stems:
            if (
                emitted_stem == raw_stem
                or emitted_stem.startswith(f'{raw_stem}.')
                or emitted_stem.endswith(f'.{raw_stem}')
            ):
                return True
    return False


def _iter_custom_query_metric_names(value: Any) -> Iterator[str]:
    if isinstance(value, dict):
        metric_type = value.get('type')
        name = value.get('name')
        if isinstance(metric_type, str) and metric_type in CUSTOM_QUERY_METRIC_TYPES and isinstance(name, str) and name:
            yield name

        for child in value.values():
            yield from _iter_custom_query_metric_names(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_custom_query_metric_names(child)


def _custom_metric_name_candidates(name: str, metric_prefix: str | None) -> Iterator[str]:
    yield name
    if metric_prefix and not name.startswith(metric_prefix):
        yield f'{metric_prefix}{name}'


def _configured_custom_metric_names(cache_dir: Path, metric_prefix: str | None) -> set[str]:
    config = _load_replay_config(cache_dir)
    sections = [config.get('init_config')]
    instances = config.get('instances')
    if isinstance(instances, list):
        sections.extend(instances)

    names = set()
    for section in sections:
        if not isinstance(section, dict):
            continue
        for key in ('custom_queries', 'global_custom_queries'):
            for name in _iter_custom_query_metric_names(section.get(key)):
                names.update(_custom_metric_name_candidates(name, metric_prefix))
    return names


def _emitted_metric_names(output: dict[str, Any]) -> set[str]:
    names = set()
    for reading_output in _normalized_reading_outputs(output):
        _assert_normalized_output_contract(reading_output)
        for metric in reading_output.get('metrics', []):
            name = metric.get('name')
            if isinstance(name, str) and name:
                names.add(name)
    return names


def _coverage_ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _format_percent(value: float | None) -> str:
    if value is None:
        return 'n/a'
    return f'{value:.1%}'


def _compute_openmetrics_coverage(
    *, cache_dir: Path, output: dict[str, Any], metadata_rows: dict[str, dict[str, str]], metric_prefix: str | None
) -> dict[str, Any]:
    observed_families = _observed_openmetrics_families(cache_dir)
    emitted_names = _emitted_metric_names(output)
    metadata_names = set(metadata_rows)
    prefixes = _load_raw_metric_prefixes(cache_dir)
    if metric_prefix:
        prefixes.add(metric_prefix)
        prefixes.add(metric_prefix.replace('.', '_'))

    observed_covered = {
        family
        for family in observed_families
        if _family_is_heuristically_emitted(family, emitted_names, prefixes=prefixes)
    }
    observed_missing = observed_families - observed_covered
    metadata_emitted = metadata_names & emitted_names
    metadata_unemitted = metadata_names - emitted_names

    return {
        'integration_prefix': metric_prefix,
        'raw_metric_prefixes': sorted(prefixes),
        'endpoint_to_emitted': {
            'coverage': _coverage_ratio(len(observed_covered), len(observed_families)),
            'covered_count': len(observed_covered),
            'missing_count': len(observed_missing),
            'endpoint_count': len(observed_families),
            'covered_families': sorted(observed_covered),
            'missing_families': sorted(observed_missing),
        },
        'metadata_to_emitted': {
            'coverage': _coverage_ratio(len(metadata_emitted), len(metadata_names)),
            'emitted_count': len(metadata_emitted),
            'unemitted_count': len(metadata_unemitted),
            'metadata_count': len(metadata_names),
            'emitted_metrics': sorted(metadata_emitted),
            'unemitted_metrics': sorted(metadata_unemitted),
        },
        'emitted_metrics': sorted(emitted_names),
    }


def _write_openmetrics_coverage(property_dir: Path, coverage: dict[str, Any]) -> None:
    property_dir.mkdir(parents=True, exist_ok=True)
    (property_dir / 'coverage.json').write_text(json.dumps(coverage, indent=2, sort_keys=True) + '\n')

    endpoint = coverage['endpoint_to_emitted']
    metadata = coverage['metadata_to_emitted']
    lines = [
        '# OpenMetrics replay coverage',
        '',
        'This is a generic, advisory coverage report. Endpoint -> emitted uses a name-stem heuristic '
        'because integrations can rename upstream families in integration-specific ways.',
        '',
        '## Summary',
        '',
        f'- Endpoint metric families: {endpoint["endpoint_count"]}',
        f'- Endpoint metric families heuristically emitted: {endpoint["covered_count"]}',
        f'- Endpoint -> emitted coverage: {_format_percent(endpoint["coverage"])}',
        f'- metadata.csv metrics: {metadata["metadata_count"]}',
        f'- metadata.csv metrics emitted by this replay: {metadata["emitted_count"]}',
        f'- metadata.csv -> emitted coverage: {_format_percent(metadata["coverage"])}',
        '',
        '## Endpoint metric families not heuristically emitted',
        '',
    ]
    lines.extend(f'- `{family}`' for family in endpoint['missing_families'][:200])
    if len(endpoint['missing_families']) > 200:
        lines.append(f'- ... {len(endpoint["missing_families"]) - 200} more')
    lines.extend(['', '## metadata.csv metrics not emitted by this replay', ''])
    lines.extend(f'- `{metric}`' for metric in metadata['unemitted_metrics'][:200])
    if len(metadata['unemitted_metrics']) > 200:
        lines.append(f'- ... {len(metadata["unemitted_metrics"]) - 200} more')
    (property_dir / 'coverage.md').write_text('\n'.join(lines) + '\n')
    write_property_result(
        property_dir,
        property_name='openmetrics-coverage',
        artifacts=[
            {'kind': 'coverage', 'path': 'coverage.json', 'format': 'json'},
            {'kind': 'coverage-markdown', 'path': 'coverage.md', 'format': 'markdown'},
        ],
        counts={
            'endpoint_families': endpoint['endpoint_count'],
            'endpoint_families_emitted': endpoint['covered_count'],
            'metadata_metrics': metadata['metadata_count'],
            'metadata_metrics_emitted': metadata['emitted_count'],
        },
        validation_family=validation_family_for_property('openmetrics-coverage'),
        requires_replay_cache=property_requires_replay_cache('openmetrics-coverage'),
    )


def _iter_asset_json_paths(repo_root: Path, integration: str) -> Iterator[tuple[str, Path]]:
    integration_root = repo_root / integration
    for asset_type in ('dashboards', 'monitors'):
        asset_root = integration_root / 'assets' / asset_type
        if not asset_root.is_dir():
            continue
        for path in sorted(asset_root.glob('*.json')):
            yield asset_type, path


def _iter_query_strings(decoded: Any) -> Iterator[str]:
    if isinstance(decoded, dict):
        for key, value in decoded.items():
            if key in {'query', 'q'} and isinstance(value, str):
                yield value
            yield from _iter_query_strings(value)
    elif isinstance(decoded, list):
        for value in decoded:
            yield from _iter_query_strings(value)


def _dashboard_template_variable_prefixes(decoded: Any) -> dict[str, str]:
    if not isinstance(decoded, dict):
        return {}

    prefixes = {}
    for variable in decoded.get('template_variables') or []:
        if not isinstance(variable, dict):
            continue
        name = variable.get('name')
        prefix = variable.get('prefix') or name
        if isinstance(name, str) and name and isinstance(prefix, str) and prefix:
            prefixes[name] = prefix
    return prefixes


def _extract_metric_names_from_query(query: str) -> tuple[str, ...]:
    return tuple(sorted(set(QUERY_METRIC_PATTERN.findall(query))))


def _extract_query_tag_keys(query: str, template_variable_prefixes: dict[str, str] | None = None) -> tuple[str, ...]:
    template_variable_prefixes = template_variable_prefixes or {}
    tag_keys = set()

    for variable_name in QUERY_TEMPLATE_VARIABLE_PATTERN.findall(query):
        tag_keys.add(template_variable_prefixes.get(variable_name, variable_name))

    for group_by in QUERY_GROUP_BY_PATTERN.findall(query):
        for tag_key in group_by.split(','):
            tag_key = tag_key.strip()
            if tag_key and tag_key != '*':
                tag_keys.add(tag_key)

    for filter_expression in QUERY_FILTER_PATTERN.findall(query):
        for tag_key in QUERY_TAG_FILTER_PATTERN.findall(filter_expression):
            tag_keys.add(tag_key)

    return tuple(sorted(tag_keys))


def _load_asset_queries(repo_root: Path, integration: str) -> list[AssetQuery]:
    queries = []
    for asset_type, path in _iter_asset_json_paths(repo_root, integration):
        decoded = json.loads(path.read_text())
        template_variable_prefixes = _dashboard_template_variable_prefixes(decoded)
        for query in _iter_query_strings(decoded):
            metric_names = _extract_metric_names_from_query(query)
            if not metric_names:
                continue
            queries.append(
                AssetQuery(
                    path=str(path.relative_to(repo_root)),
                    asset_type=asset_type,
                    query=query,
                    metric_names=metric_names,
                    tag_keys=_extract_query_tag_keys(query, template_variable_prefixes),
                )
            )
    return queries


def _asset_metric_metadata_findings(
    *, repo_root: Path, integration: str, metadata_rows: dict[str, dict[str, str]]
) -> list[ReplayPBTFinding]:
    prefix = _load_manifest_metric_prefix(repo_root, integration)
    if not prefix:
        return [
            ReplayPBTFinding(
                level='warning',
                check='asset-query-metrics-in-metadata',
                message='Integration manifest does not declare a metric prefix; asset metric metadata check skipped.',
            )
        ]

    findings = []
    for asset_query in _load_asset_queries(repo_root, integration):
        for metric_name in asset_query.metric_names:
            if not metric_name.startswith(prefix) or metric_name in metadata_rows:
                continue
            findings.append(
                ReplayPBTFinding(
                    level='error',
                    check='asset-query-metrics-in-metadata',
                    message='Integration asset query references a metric missing from metadata.csv.',
                    path=asset_query.path,
                    query=asset_query.query,
                    metric=metric_name,
                    asset_type=asset_query.asset_type,
                )
            )
    return findings


def _emitted_metric_tag_keys(output: dict[str, Any]) -> dict[str, set[str]]:
    metric_tag_keys = {}
    for reading_output in _normalized_reading_outputs(output):
        _assert_normalized_output_contract(reading_output)
        for metric in reading_output.get('metrics', []):
            name = metric.get('name')
            if not isinstance(name, str) or not name:
                continue
            keys = metric_tag_keys.setdefault(name, set())
            for tag in metric.get('tags') or []:
                if ':' in tag:
                    keys.add(tag.split(':', 1)[0])
    return metric_tag_keys


def _asset_query_replay_tag_findings(
    *, repo_root: Path, integration: str, output: dict[str, Any], metadata_rows: dict[str, dict[str, str]]
) -> list[ReplayPBTFinding]:
    prefix = _load_manifest_metric_prefix(repo_root, integration)
    emitted_tag_keys = _emitted_metric_tag_keys(output)
    emitted_metric_names = set(emitted_tag_keys)
    findings = []

    for asset_query in _load_asset_queries(repo_root, integration):
        for metric_name in asset_query.metric_names:
            if (
                prefix
                and metric_name.startswith(prefix)
                and metric_name in metadata_rows
                and metric_name not in emitted_metric_names
            ):
                findings.append(
                    ReplayPBTFinding(
                        level='warning',
                        check='asset-query-tags-seen-in-replay',
                        message='Integration asset query metric was not emitted by this replay fixture.',
                        path=asset_query.path,
                        query=asset_query.query,
                        metric=metric_name,
                        asset_type=asset_query.asset_type,
                    )
                )
                continue

            if metric_name not in emitted_metric_names:
                continue

            missing_tag_keys = set(asset_query.tag_keys) - emitted_tag_keys[metric_name]
            for tag_key in sorted(missing_tag_keys):
                findings.append(
                    ReplayPBTFinding(
                        level='warning',
                        check='asset-query-tags-seen-in-replay',
                        message='Integration asset query tag key was not seen on emitted replay metric.',
                        path=asset_query.path,
                        query=asset_query.query,
                        metric=metric_name,
                        tag_key=tag_key,
                        asset_type=asset_query.asset_type,
                    )
                )
    return findings


def _write_findings(property_dir: Path, findings: list[ReplayPBTFinding]) -> None:
    property_dir.mkdir(parents=True, exist_ok=True)
    serialized = [finding.as_dict() for finding in findings]
    (property_dir / 'findings.json').write_text(json.dumps(serialized, indent=2, sort_keys=True) + '\n')

    lines = ['# Replay validation findings', '']
    if not findings:
        lines.append('No findings.')
    for finding in findings:
        lines.extend(
            [
                f'- **{finding.level.upper()}** `{finding.check}`: {finding.message}',
                f'  - metric: `{finding.metric}`' if finding.metric else '',
                f'  - tag key: `{finding.tag_key}`' if finding.tag_key else '',
                f'  - path: `{finding.path}`' if finding.path else '',
                f'  - query: `{finding.query}`' if finding.query else '',
            ]
        )
    (property_dir / 'warnings.md').write_text('\n'.join(line for line in lines if line) + '\n')
    property_name = findings[0].check if findings else property_dir.name
    write_property_result(
        property_dir,
        property_name=property_name,
        artifacts=[
            {'kind': 'findings', 'path': 'findings.json', 'format': 'json'},
            {'kind': 'findings-markdown', 'path': 'warnings.md', 'format': 'markdown'},
        ],
        counts={
            'errors': sum(1 for finding in findings if finding.level == 'error'),
            'warnings': sum(1 for finding in findings if finding.level == 'warning'),
        },
        validation_family=validation_family_for_property(property_name),
        requires_replay_cache=property_requires_replay_cache(property_name),
    )


def _handle_findings(context: ReplayPBTContext, property_name: str, findings: list[ReplayPBTFinding]) -> None:
    _write_findings(context.artifacts / property_name, findings)

    for finding in findings:
        if finding.level == 'warning':
            warnings.warn(f'{finding.check}: {finding.message}', ReplayPBTWarning, stacklevel=2)

    failures = [
        finding
        for finding in findings
        if finding.level == 'error' or (context.warnings_as_errors and finding.level == 'warning')
    ]
    assert not failures, f'{property_name} findings: {[finding.as_dict() for finding in failures[:20]]!r}'


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


def _assert_emitted_metrics_match_metadata(
    output: dict[str, Any],
    metadata_rows: dict[str, dict[str, str]],
    *,
    configured_custom_metrics: set[str] | None = None,
) -> None:
    configured_custom_metrics = configured_custom_metrics or set()
    missing = []
    mismatched = []
    emitted_count = 0
    validated_count = 0
    for reading_output in _normalized_reading_outputs(output):
        _assert_normalized_output_contract(reading_output)
        emitted_count += len(reading_output.get('metrics', []))
        for metric in reading_output.get('metrics', []):
            name = metric.get('name')
            if name in configured_custom_metrics:
                continue

            validated_count += 1
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

    if emitted_count == 0:
        pytest.skip('No metrics emitted by this replay cache.')
    if validated_count == 0:
        pytest.skip('Only configured custom metrics were emitted by this replay cache.')
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


def test_normalized_output_match_identifies_order_only_differences():
    original = {
        'metrics': [
            {'name': 'example.a', 'type': 0, 'value': 1.0, 'tags': []},
            {'name': 'example.b', 'type': 0, 'value': 1.0, 'tags': []},
        ],
        'service_checks': [],
    }
    mutated = {'metrics': list(reversed(original['metrics'])), 'service_checks': []}

    with pytest.raises(AssertionError, match='differs only by ordering'):
        _assert_normalized_outputs_match(original, mutated)


def test_run_compare_check_cache_reports_missing_diff_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    context = ReplayPBTContext(
        {
            'integration': 'example',
            'environment': 'py3',
            'replay_cache': str(tmp_path / 'cache'),
            'artifacts': str(tmp_path / 'artifacts'),
        }
    )

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=args, returncode=0, stdout='compare stdout', stderr='compare stderr')

    monkeypatch.setattr(subprocess, 'run', fake_run)

    with pytest.raises(AssertionError, match='compare-check did not write') as exc_info:
        _run_compare_check_cache(context=context, cache=context.cache, artifacts=context.artifacts)

    message = str(exc_info.value)
    assert 'diff.json' in message
    assert 'compare stdout' in message
    assert 'compare stderr' in message


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


def test_emitted_metrics_match_metadata_skips_no_metric_output():
    output = {'metrics': [], 'service_checks': []}

    with pytest.raises(pytest.skip.Exception, match='No metrics emitted'):
        _assert_emitted_metrics_match_metadata(output, {})


def test_load_metadata_rows_or_skip_skips_missing_metadata_csv(tmp_path: Path):
    with pytest.raises(pytest.skip.Exception, match='has no metadata.csv'):
        _load_metadata_rows_or_skip(tmp_path, 'openmetrics')


def test_configured_custom_metric_names_extracts_custom_queries(tmp_path: Path):
    cache = tmp_path / 'cache'
    cache.mkdir()
    (cache / 'config.json').write_text(
        json.dumps(
            {
                'init_config': {
                    'global_custom_queries': [{'columns': [{'name': 'global.custom.metric', 'type': 'gauge'}]}]
                },
                'instances': [
                    {
                        'custom_queries': [
                            {
                                'columns': [
                                    {'name': 'custom.heroes.count', 'type': 'gauge'},
                                    {'name': 'dynamic_tag', 'type': 'tag'},
                                ]
                            }
                        ]
                    },
                    {'custom_queries': [{'columns': [{'name': 'elasticsearch.custom.metric', 'type': 'gauge'}]}]},
                ],
            }
        )
    )

    assert _configured_custom_metric_names(cache, 'voltdb.') == {
        'global.custom.metric',
        'voltdb.global.custom.metric',
        'custom.heroes.count',
        'voltdb.custom.heroes.count',
        'elasticsearch.custom.metric',
        'voltdb.elasticsearch.custom.metric',
    }


def test_emitted_metrics_match_metadata_ignores_configured_custom_metrics():
    output = {
        'metrics': [
            {'name': 'example.metric', 'type': 0, 'value': 1.0, 'tags': []},
            {'name': 'example.custom.metric', 'type': 0, 'value': 2.0, 'tags': []},
        ],
        'service_checks': [],
    }

    _assert_emitted_metrics_match_metadata(
        output,
        {'example.metric': {'metric_type': 'gauge'}},
        configured_custom_metrics={'example.custom.metric'},
    )


def test_emitted_metrics_match_metadata_rejects_missing_metric():
    output = {'metrics': [{'name': 'missing.metric', 'type': 0, 'value': 1.0, 'tags': []}], 'service_checks': []}

    with pytest.raises(AssertionError, match='missing from metadata'):
        _assert_emitted_metrics_match_metadata(output, {})


def test_emitted_metrics_match_metadata_rejects_type_mismatch():
    output = {'metrics': [{'name': 'example.metric', 'type': 0, 'value': 1.0, 'tags': []}], 'service_checks': []}
    metadata_rows = {'example.metric': {'metric_type': 'count'}}

    with pytest.raises(AssertionError, match='type mismatches'):
        _assert_emitted_metrics_match_metadata(output, metadata_rows)


def test_repeated_run_tag_stability_rejects_duplicate_check_tags():
    envelope = {
        'version': 2,
        'readings': [
            {
                'index': 0,
                'output': {
                    'metrics': [],
                    'service_checks': [],
                    'check_states': [{'index': 0, 'class': 'Example', 'tags': ['flavor:mysql']}],
                },
            },
            {
                'index': 1,
                'output': {
                    'metrics': [],
                    'service_checks': [],
                    'check_states': [{'index': 0, 'class': 'Example', 'tags': ['flavor:mysql', 'flavor:mysql']}],
                },
            },
        ],
    }

    with pytest.raises(AssertionError, match='contain duplicates'):
        _assert_repeated_run_tag_stability(envelope)


def test_repeated_run_tag_stability_rejects_check_tag_growth():
    envelope = {
        'version': 2,
        'readings': [
            {
                'index': 0,
                'output': {
                    'metrics': [],
                    'service_checks': [],
                    'check_states': [{'index': 0, 'class': 'Example', 'tags': ['flavor:mysql']}],
                },
            },
            {
                'index': 1,
                'output': {
                    'metrics': [],
                    'service_checks': [],
                    'check_states': [{'index': 0, 'class': 'Example', 'tags': ['extra:true', 'flavor:mysql']}],
                },
            },
        ],
    }

    with pytest.raises(AssertionError, match='grew or changed'):
        _assert_repeated_run_tag_stability(envelope)


def test_repeated_run_tag_stability_accepts_stable_check_tags():
    envelope = {
        'version': 2,
        'readings': [
            {
                'index': 0,
                'output': {
                    'metrics': [{'name': 'example.metric', 'type': 0, 'value': 1.0, 'tags': ['flavor:mysql']}],
                    'service_checks': [],
                    'check_states': [{'index': 0, 'class': 'Example', 'tags': ['flavor:mysql']}],
                },
            },
            {
                'index': 1,
                'output': {
                    'metrics': [{'name': 'example.metric', 'type': 0, 'value': 2.0, 'tags': ['flavor:mysql']}],
                    'service_checks': [],
                    'check_states': [{'index': 0, 'class': 'Example', 'tags': ['flavor:mysql']}],
                },
            },
        ],
    }

    _assert_repeated_run_tag_stability(envelope)


def test_openmetrics_coverage_counts_endpoint_and_metadata_directions(tmp_path: Path):
    cache = tmp_path / 'cache'
    cache.mkdir()
    (cache / 'config.json').write_text(json.dumps({'instances': [{'raw_metric_prefix': 'n8n_'}]}))
    (cache / 'capture.json').write_text(json.dumps({'files': {'requests': 'capture.requests.json'}}))
    (cache / 'capture.requests.json').write_text(
        json.dumps(
            [
                {
                    'body': '\n'.join(
                        [
                            '# TYPE n8n_workflow_execution_duration_seconds histogram',
                            'n8n_workflow_execution_duration_seconds_bucket{le="1"} 1',
                            'n8n_workflow_execution_duration_seconds_sum 2',
                            'n8n_unmapped_total 3',
                        ]
                    ),
                    'headers': {'Content-Type': 'text/plain'},
                }
            ]
        )
    )
    output = {
        'metrics': [
            {'name': 'n8n.workflow.execution.duration.seconds.count', 'type': 3, 'value': 1.0, 'tags': []},
            {'name': 'n8n.workflow.execution.duration.seconds.sum', 'type': 0, 'value': 2.0, 'tags': []},
        ],
        'service_checks': [],
    }

    coverage = _compute_openmetrics_coverage(
        cache_dir=cache,
        output=output,
        metadata_rows={
            'n8n.workflow.execution.duration.seconds.count': {'metric_type': 'count'},
            'n8n.workflow.execution.duration.seconds.sum': {'metric_type': 'gauge'},
            'n8n.not.emitted': {'metric_type': 'gauge'},
        },
        metric_prefix='n8n.',
    )

    assert coverage['endpoint_to_emitted']['endpoint_count'] == 2
    assert coverage['endpoint_to_emitted']['covered_families'] == ['n8n_workflow_execution_duration_seconds']
    assert coverage['endpoint_to_emitted']['missing_families'] == ['n8n_unmapped']
    assert coverage['metadata_to_emitted']['metadata_count'] == 3
    assert coverage['metadata_to_emitted']['emitted_count'] == 2


def test_write_openmetrics_coverage_artifacts(tmp_path: Path):
    coverage = {
        'endpoint_to_emitted': {
            'coverage': 0.5,
            'covered_count': 1,
            'missing_count': 1,
            'endpoint_count': 2,
            'missing_families': ['missing_raw_family'],
        },
        'metadata_to_emitted': {
            'coverage': 0.25,
            'emitted_count': 1,
            'unemitted_count': 3,
            'metadata_count': 4,
            'unemitted_metrics': ['example.not_emitted'],
        },
        'emitted_metrics': ['example.emitted'],
    }

    _write_openmetrics_coverage(tmp_path, coverage)

    assert json.loads((tmp_path / 'coverage.json').read_text())['endpoint_to_emitted']['coverage'] == 0.5
    assert 'Endpoint -> emitted coverage: 50.0%' in (tmp_path / 'coverage.md').read_text()
    result = json.loads((tmp_path / 'property-result.json').read_text())
    assert result['property'] == 'openmetrics-coverage'
    assert [artifact['path'] for artifact in result['artifacts']] == ['coverage.json', 'coverage.md']


def _write_asset_query_fixture(repo_root: Path) -> None:
    integration_root = repo_root / 'example'
    (integration_root / 'assets' / 'dashboards').mkdir(parents=True)
    (integration_root / 'assets' / 'monitors').mkdir(parents=True)
    (integration_root / 'manifest.json').write_text(
        json.dumps({'assets': {'integration': {'metrics': {'prefix': 'example.'}}}})
    )
    (integration_root / 'assets' / 'dashboards' / 'overview.json').write_text(
        json.dumps(
            {
                'template_variables': [{'name': 'service', 'prefix': 'service'}],
                'widgets': [
                    {
                        'definition': {
                            'requests': [
                                {'queries': [{'query': 'avg:example.request.count{$service,status:ok} by {endpoint}'}]}
                            ]
                        }
                    }
                ],
            }
        )
    )
    (integration_root / 'assets' / 'monitors' / 'latency.json').write_text(
        json.dumps({'definition': {'query': 'avg(last_5m):avg:external.request.count{*} > 1'}})
    )


def test_extract_metric_names_from_query_handles_nested_monitor_query():
    assert _extract_metric_names_from_query(
        "avg(last_4h):anomalies(avg:haproxy.backend.denied.resp_rate{*} by {host}, 'agile') >= 1"
    ) == ('haproxy.backend.denied.resp_rate',)


def test_extract_query_tag_keys_maps_dashboard_template_variables():
    assert _extract_query_tag_keys(
        'sum:example.request.count{$service,status:ok,error_type IN (timeout)} by {endpoint}',
        {'service': 'service_name'},
    ) == ('endpoint', 'error_type', 'service_name', 'status')


def test_asset_metric_metadata_findings_ignore_external_metrics(tmp_path: Path):
    _write_asset_query_fixture(tmp_path)

    findings = _asset_metric_metadata_findings(
        repo_root=tmp_path,
        integration='example',
        metadata_rows={'example.request.count': {'metric_type': 'count'}},
    )

    assert findings == []


def test_asset_metric_metadata_findings_report_missing_integration_metric(tmp_path: Path):
    _write_asset_query_fixture(tmp_path)

    findings = _asset_metric_metadata_findings(repo_root=tmp_path, integration='example', metadata_rows={})

    assert len(findings) == 1
    assert findings[0].level == 'error'
    assert findings[0].metric == 'example.request.count'
    assert findings[0].path == 'example/assets/dashboards/overview.json'


def test_asset_query_replay_tag_findings_warn_on_unemitted_metric_and_missing_tags(tmp_path: Path):
    _write_asset_query_fixture(tmp_path)
    output = {
        'metrics': [{'name': 'example.request.count', 'type': 0, 'value': 1.0, 'tags': ['service:api']}],
        'service_checks': [],
    }

    findings = _asset_query_replay_tag_findings(
        repo_root=tmp_path,
        integration='example',
        output=output,
        metadata_rows={'example.request.count': {'metric_type': 'count'}, 'example.other': {'metric_type': 'gauge'}},
    )

    assert {(finding.level, finding.metric, finding.tag_key, finding.asset_type) for finding in findings} == {
        ('warning', 'example.request.count', 'endpoint', 'dashboards'),
        ('warning', 'example.request.count', 'status', 'dashboards'),
    }


def test_handle_findings_writes_artifacts_and_can_promote_warnings_to_errors(tmp_path: Path):
    context = ReplayPBTContext(
        {
            'integration': 'example',
            'environment': 'py3',
            'replay_cache': str(tmp_path / 'cache'),
            'artifacts': str(tmp_path / 'artifacts'),
            'warnings_as_errors': True,
        }
    )
    findings = [
        ReplayPBTFinding(
            level='warning',
            check='asset-query-tags-seen-in-replay',
            message='warning promoted to error',
        )
    ]

    with pytest.warns(ReplayPBTWarning), pytest.raises(AssertionError, match='warning promoted to error'):
        _handle_findings(context, 'asset-query-tags-seen-in-replay', findings)

    property_dir = tmp_path / 'artifacts' / 'asset-query-tags-seen-in-replay'
    assert (property_dir / 'findings.json').is_file()
    assert (property_dir / 'warnings.md').is_file()
    result = json.loads((property_dir / 'property-result.json').read_text())
    assert result['property'] == 'asset-query-tags-seen-in-replay'
    assert result['counts'] == {'errors': 0, 'warnings': 1}


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
@given(validation=st.sampled_from(['latest-release-diff']))
def test_latest_release_output_matches_target(replay_pbt_context: ReplayPBTContext, validation: str):
    # Differential property: replay the same cached fixture through the latest
    # released integration code and through the target ref. Any output diff is a
    # release-to-PR behavior change that should be reviewed as intentional or not.
    property_name = 'latest-release-diff'
    _skip_unselected(replay_pbt_context, property_name)
    assert validation == 'latest-release-diff'

    if replay_pbt_context.fixture_ref == replay_pbt_context.target_ref:
        pytest.skip('latest-release-diff requires a distinct latest release tag and target ref.')

    property_dir = replay_pbt_context.artifacts / property_name
    diff = _run_compare_check_cache(
        context=replay_pbt_context,
        cache=replay_pbt_context.cache,
        artifacts=property_dir,
        allow_diff=True,
    )
    _write_release_diff_artifacts(property_dir, diff, context=replay_pbt_context)

    assert diff['changed'] is False, 'Output changed compared to the latest release; review release diff findings.'


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
@given(mutation=st.sampled_from(['sort-json-object-keys']))
def test_json_object_key_order_mutated_cache_matches_original_output(
    replay_pbt_context: ReplayPBTContext, mutation: str
):
    # Metamorphic JSON property: object member order is not semantically
    # meaningful, so sorting JSON response object keys should not change
    # normalized Datadog check output.
    property_name = 'json-object-key-order'
    _skip_unselected(replay_pbt_context, property_name)
    assert mutation == 'sort-json-object-keys'

    _assert_mutated_cache_matches_original_output(
        context=replay_pbt_context,
        property_name=property_name,
        mutate_cache=mutate_request_capture_json_object_key_order,
        no_change_reason='Replay cache has no JSON request records with reorderable object keys.',
    )


@settings(max_examples=1, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(mutation=st.sampled_from(['change-json-whitespace']))
def test_json_whitespace_mutated_cache_matches_original_output(replay_pbt_context: ReplayPBTContext, mutation: str):
    # Metamorphic JSON property: insignificant JSON whitespace does not affect
    # decoded values, so reserializing captured JSON response bodies should not
    # change normalized Datadog check output.
    property_name = 'json-whitespace'
    _skip_unselected(replay_pbt_context, property_name)
    assert mutation == 'change-json-whitespace'

    _assert_mutated_cache_matches_original_output(
        context=replay_pbt_context,
        property_name=property_name,
        mutate_cache=mutate_request_capture_json_whitespace,
        no_change_reason='Replay cache has no JSON request records.',
    )


@settings(max_examples=1, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(mutation=st.sampled_from(['normalize-json-string-escapes']))
def test_json_string_escape_mutated_cache_matches_original_output(replay_pbt_context: ReplayPBTContext, mutation: str):
    # Metamorphic JSON property: different JSON string escaping that decodes to
    # the same values should not affect check output.
    property_name = 'json-string-escapes'
    _skip_unselected(replay_pbt_context, property_name)
    assert mutation == 'normalize-json-string-escapes'

    _assert_mutated_cache_matches_original_output(
        context=replay_pbt_context,
        property_name=property_name,
        mutate_cache=mutate_request_capture_json_string_escapes,
        no_change_reason='Replay cache has no JSON request records.',
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
    metadata_rows = _load_metadata_rows_or_skip(replay_pbt_context.repo, replay_pbt_context.integration)
    configured_custom_metrics = _configured_custom_metric_names(
        property_dir,
        _load_manifest_metric_prefix(replay_pbt_context.repo, replay_pbt_context.integration),
    )
    _assert_emitted_metrics_match_metadata(
        _read_normalized(property_dir), metadata_rows, configured_custom_metrics=configured_custom_metrics
    )


@settings(max_examples=1, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(validation=st.sampled_from(['repeated-run-tag-stability']))
def test_repeated_run_tags_are_stable(replay_pbt_context: ReplayPBTContext, validation: str):
    # Stateful repeated-run property: compare-check reuses the same check
    # instance across readings. Check-level tag attributes and emitted context
    # tags should converge after the first run, not grow on every check run.
    # This targets bugs like a database integration appending a version/resource
    # tag to self.tags on each invocation.
    property_name = 'repeated-run-tag-stability'
    _skip_unselected(replay_pbt_context, property_name)
    assert validation == 'repeated-run-tag-stability'

    property_dir = replay_pbt_context.artifacts / property_name
    diff = _run_compare_check_cache(context=replay_pbt_context, cache=replay_pbt_context.cache, artifacts=property_dir)
    assert diff['changed'] is False
    _assert_repeated_run_tag_stability(_read_normalized(property_dir))


@settings(max_examples=1, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(validation=st.sampled_from(['openmetrics-coverage']))
def test_openmetrics_replay_coverage(replay_pbt_context: ReplayPBTContext, validation: str):
    # Coverage/report property: for replay caches containing Prometheus/OpenMetrics
    # response bodies, report both observed-upstream-family -> emitted Datadog
    # coverage and supported metadata metric -> emitted-in-this-env coverage.
    # The observed direction is heuristic because integrations may rename raw
    # families in integration-specific ways; this property writes artifacts and
    # does not impose thresholds by default.
    property_name = 'openmetrics-coverage'
    _skip_unselected(replay_pbt_context, property_name)
    assert validation == 'openmetrics-coverage'

    property_dir = replay_pbt_context.artifacts / property_name
    diff = _run_compare_check_cache(context=replay_pbt_context, cache=replay_pbt_context.cache, artifacts=property_dir)
    assert diff['changed'] is False
    if not _observed_openmetrics_families(property_dir):
        pytest.skip('Replay cache has no request records with OpenMetrics samples.')

    metadata_rows = _load_metadata_rows(replay_pbt_context.repo, replay_pbt_context.integration)
    coverage = _compute_openmetrics_coverage(
        cache_dir=property_dir,
        output=_read_normalized(property_dir),
        metadata_rows=metadata_rows,
        metric_prefix=_load_manifest_metric_prefix(replay_pbt_context.repo, replay_pbt_context.integration),
    )
    _write_openmetrics_coverage(property_dir, coverage)


@settings(max_examples=1, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(validation=st.sampled_from(['asset-query-tags-seen-in-replay']))
def test_asset_query_tags_are_seen_in_replay(replay_pbt_context: ReplayPBTContext, validation: str):
    # Replay coverage signal: asset metrics/tags can be valid globally while the
    # current fixture still fails to exercise them.
    property_name = 'asset-query-tags-seen-in-replay'
    _skip_unselected(replay_pbt_context, property_name)
    assert validation == 'asset-query-tags-seen-in-replay'

    asset_queries = _load_asset_queries(replay_pbt_context.repo, replay_pbt_context.integration)
    if not asset_queries:
        pytest.skip('Integration has no dashboard or monitor metric queries to compare with replay output.')

    property_dir = replay_pbt_context.artifacts / property_name
    diff = _run_compare_check_cache(context=replay_pbt_context, cache=replay_pbt_context.cache, artifacts=property_dir)
    assert diff['changed'] is False
    metadata_rows = _load_metadata_rows(replay_pbt_context.repo, replay_pbt_context.integration)
    findings = _asset_query_replay_tag_findings(
        repo_root=replay_pbt_context.repo,
        integration=replay_pbt_context.integration,
        output=_read_normalized(property_dir),
        metadata_rows=metadata_rows,
    )
    _handle_findings(replay_pbt_context, property_name, findings)


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

    # First materialize auto/latest caches into an exact compare-check artifact
    # directory. Mutating the materialized cache keeps cache selection and
    # fixture compatibility logic centralized in compare-check.
    original_diff = _run_compare_check_cache(context=context, cache=context.cache, artifacts=original)
    assert original_diff['changed'] is False

    mutated_cache = copy_replay_cache(original, property_dir / 'mutated-cache')
    changed_records = mutate_cache(mutated_cache)
    if changed_records == 0:
        pytest.skip(no_change_reason)

    mutated_diff = _run_compare_check_cache(context=context, cache=mutated_cache, artifacts=mutated)

    assert mutated_diff['changed'] is False
    _assert_normalized_outputs_match(_read_normalized(original), _read_normalized(mutated))
