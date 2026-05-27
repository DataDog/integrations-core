# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Empirically map OpenMetrics endpoint families to emitted Datadog metrics."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

from datadog_checks.dev.replay.pbt.openmetrics import parse_sample_line

OPENMETRICS_COMMENT_RE = re.compile(r'^#\s+(?:HELP|TYPE)\s+(?P<name>[A-Za-z_:][A-Za-z0-9_:]*)\b')
OPENMETRICS_SUFFIXES = ('_bucket', '_total', '_sum', '_count')


def raw_openmetrics_family_name(sample_name: str) -> str:
    for suffix in OPENMETRICS_SUFFIXES:
        if sample_name.endswith(suffix):
            return sample_name[: -len(suffix)]
    return sample_name


def request_capture_files(cache_dir: Path) -> list[Path]:
    manifest_path = cache_dir / 'capture.json'
    manifest = json.loads(manifest_path.read_text())
    if isinstance(manifest, dict):
        files = manifest.get('files', {})
        requests_file = files.get('requests') if isinstance(files, dict) else None
        return [cache_dir / str(requests_file)] if requests_file else []
    if isinstance(manifest, list):
        return [manifest_path]
    return []


def request_record_has_openmetrics_samples(record: dict[str, Any]) -> bool:
    body = record.get('body')
    return isinstance(body, str) and any(parse_sample_line(line) is not None for line in body.split('\n'))


def filter_openmetrics_body_to_family(body: str, family: str) -> str:
    lines = []
    for line in body.split('\n'):
        sample = parse_sample_line(line)
        if sample is not None:
            if raw_openmetrics_family_name(sample.name) == family:
                lines.append(line)
            continue

        match = OPENMETRICS_COMMENT_RE.match(line)
        if match and raw_openmetrics_family_name(match.group('name')) == family:
            lines.append(line)
    return '\n'.join(lines)


def observed_openmetrics_families(cache_dir: Path) -> list[str]:
    families = set()
    for capture_file in request_capture_files(cache_dir):
        records = json.loads(capture_file.read_text())
        if not isinstance(records, list):
            continue
        for record in records:
            body = record.get('body') if isinstance(record, dict) else None
            if not isinstance(body, str):
                continue
            for line in body.split('\n'):
                sample = parse_sample_line(line)
                if sample is not None:
                    families.add(raw_openmetrics_family_name(sample.name))
    return sorted(families)


def write_single_family_fixture(cache_dir: Path, fixture_dir: Path, family: str) -> Path:
    fixture_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = cache_dir / 'capture.json'
    manifest = json.loads(manifest_path.read_text())

    if isinstance(manifest, dict):
        files = manifest.get('files', {})
        requests_file = files.get('requests') if isinstance(files, dict) else None
        if not requests_file:
            raise RuntimeError('Replay cache manifest does not contain a requests fixture file.')
        request_path = cache_dir / str(requests_file)
        output_request_path = fixture_dir / str(requests_file)
        output_request_path.parent.mkdir(parents=True, exist_ok=True)
        write_filtered_request_records(request_path, output_request_path, family)
        (fixture_dir / 'capture.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
        return fixture_dir / 'capture.json'

    if isinstance(manifest, list):
        write_filtered_request_records(manifest_path, fixture_dir / 'capture.json', family)
        return fixture_dir / 'capture.json'

    raise RuntimeError('Unsupported replay cache manifest shape for empirical OpenMetrics mapping.')


def write_filtered_request_records(source: Path, destination: Path, family: str) -> None:
    records = json.loads(source.read_text())
    if not isinstance(records, list):
        raise RuntimeError(f'Request fixture is not a list: {source}')

    filtered_records = []
    for record in records:
        if isinstance(record, dict) and request_record_has_openmetrics_samples(record):
            record = dict(record)
            record['body'] = filter_openmetrics_body_to_family(str(record['body']), family)
        filtered_records.append(record)

    destination.write_text(json.dumps(filtered_records, indent=2, sort_keys=True) + '\n')


def safe_path_component(value: str) -> str:
    return re.sub(r'[^A-Za-z0-9_.-]+', '_', value).strip('._') or 'family'


def write_pytest_file(path: Path, args: argparse.Namespace) -> None:
    path.write_text(
        f'''
import json
import time
from pathlib import Path

from datadog_checks.dev.replay.adapters import install_replay_adapters
from datadog_checks.dev.replay.openmetrics_mapper import safe_path_component, write_single_family_fixture
from datadog_checks.dev.replay.output import reset_serialized_output, serialize_aggregator
from datadog_checks.dev.replay.pytest import build_check_instances


def _emitted_metric_names(serialized):
    names = set()
    for reading in serialized.get('readings', []):
        for metric in reading.get('output', {{}}).get('metrics', []):
            name = metric.get('name')
            if isinstance(name, str) and name:
                names.add(name)
    return sorted(names)


def test_empirical_openmetrics_mapping(monkeypatch, aggregator, datadog_agent, dd_run_check):
    from datadog_checks.base.utils import time as dd_time

    cache_dir = Path({str(args.cache)!r})
    output_path = Path({str(args.output)!r})
    work_dir = Path({str(args.work_dir)!r})
    families = {args.families!r}
    config = json.loads(Path({str(args.config)!r}).read_text())
    init_config = config.get('init_config') or {{}}
    instances = config.get('instances', [config])
    adapters = {args.adapters_tuple!r}
    current_time = [{args.replay_time!r}]
    real_perf_counter = time.perf_counter

    monkeypatch.setattr(time, 'time', lambda: current_time[0])
    monkeypatch.setattr(time, 'monotonic', lambda: current_time[0])
    monkeypatch.setattr(time, 'perf_counter', lambda: current_time[0])
    monkeypatch.setattr(dd_time, 'epoch_offset', lambda: current_time[0])
    monkeypatch.setattr(dd_time, 'time_func', lambda: current_time[0])

    results = []
    loop_start = real_perf_counter()
    for family in families:
        fixture_path = write_single_family_fixture(cache_dir, work_dir / safe_path_component(family), family)
        family_start = real_perf_counter()
        reset_serialized_output(aggregator, datadog_agent)
        outputs = []
        with monkeypatch.context() as adapter_patch:
            adapter_records = install_replay_adapters(
                adapter_patch,
                'replay',
                fixture_path,
                {args.check_name!r},
                adapters=adapters,
            )
            checks = build_check_instances(
                {args.check_class!r}, instances, {args.check_name!r}, init_config=init_config
            )
            for index in range({args.readings!r}):
                current_time[0] = {args.replay_time!r} + index * {args.reading_interval!r}
                for check in checks:
                    dd_run_check(check)
                outputs.append(
                    {{
                        'index': index,
                        'output': serialize_aggregator(
                            aggregator,
                            datadog_agent,
                            checks=checks,
                            adapter_records=adapter_records,
                        ),
                    }}
                )
                if index + 1 < {args.readings!r}:
                    reset_serialized_output(aggregator, datadog_agent)
        serialized = {{'version': 2, 'readings': outputs}}
        results.append(
            {{
                'family': family,
                'emitted_metrics': _emitted_metric_names(serialized),
                'elapsed_s': real_perf_counter() - family_start,
            }}
        )

    mapped_results = [result for result in results if result['emitted_metrics']]
    total_elapsed = real_perf_counter() - loop_start
    output = {{
        'method': 'isolated-family-replay',
        'family_count': len(results),
        'mapped_count': len(mapped_results),
        'unmapped_count': len(results) - len(mapped_results),
        'coverage': (len(mapped_results) / len(results)) if results else None,
        'elapsed_s': total_elapsed,
        'avg_family_elapsed_s': (total_elapsed / len(results)) if results else None,
        'family_mappings': results,
    }}
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + '\\n')
'''
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--check-name', required=True)
    parser.add_argument('--check-class')
    parser.add_argument('--readings', type=int, default=1)
    parser.add_argument('--replay-time', type=float, default=1_700_000_000.0)
    parser.add_argument('--reading-interval', type=float, default=15.0)
    parser.add_argument('--adapters', default='all')
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.readings < 1:
        raise SystemExit('--readings must be >= 1')
    args.families = observed_openmetrics_families(args.cache)
    if args.adapters == 'all':
        args.adapters_tuple = None
    else:
        args.adapters_tuple = tuple(adapter.strip() for adapter in args.adapters.split(',') if adapter.strip())
    args.output.parent.mkdir(parents=True, exist_ok=True)

    try:
        import pytest
    except Exception as e:
        print(f'pytest is required for empirical OpenMetrics mapping: {e}', file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix='openmetrics-family-map-') as tmpdir:
        args.work_dir = Path(tmpdir) / 'fixtures'
        test_file = Path(tmpdir) / 'test_empirical_openmetrics_mapping.py'
        write_pytest_file(test_file, args)
        return pytest.main(['-q', str(test_file)])


if __name__ == '__main__':
    raise SystemExit(main())
