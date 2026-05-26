# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from datadog_checks.dev.replay.adapters import ADAPTERS


def _write_pytest_file(path: Path, args: argparse.Namespace) -> None:
    path.write_text(
        f'''
import json
from pathlib import Path

from datadog_checks.dev.replay.adapters import install_replay_adapters, write_fixture_manifest, read_fixture_manifest
from datadog_checks.dev.replay.output import reset_serialized_output, serialize_aggregator
from datadog_checks.dev.replay.pytest import build_check_instances


def test_replay_check_runner(monkeypatch, aggregator, datadog_agent, dd_run_check):
    from datadog_checks.base.utils import time as dd_time
    import time

    current_time = [{args.replay_time!r}]
    monkeypatch.setattr(time, 'time', lambda: current_time[0])
    monkeypatch.setattr(time, 'monotonic', lambda: current_time[0])
    monkeypatch.setattr(time, 'perf_counter', lambda: current_time[0])
    monkeypatch.setattr(dd_time, 'epoch_offset', lambda: current_time[0])
    monkeypatch.setattr(dd_time, 'time_func', lambda: current_time[0])

    config = json.loads(Path({str(args.config)!r}).read_text())
    init_config = config.get('init_config') or {{}}
    instances = config.get('instances', [config])
    fixture = Path({str(args.fixture)!r})
    adapter_records = install_replay_adapters(
        monkeypatch,
        {args.mode!r},
        fixture,
        {args.check_name!r},
        adapters={args.adapters_tuple!r},
    )

    readings = {args.readings!r}
    checks = build_check_instances({args.check_class!r}, instances, {args.check_name!r}, init_config=init_config)
    outputs = []
    for index in range(readings):
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
        if index + 1 < readings:
            reset_serialized_output(aggregator, datadog_agent)

    if {args.mode!r} == 'record':
        manifest = write_fixture_manifest(fixture, adapter_records, readings=readings)
        assert manifest['adapters'], 'Replay adapters captured zero records during record mode'
    else:
        manifest = read_fixture_manifest(fixture)
        assert manifest['adapters'], 'Replay fixture has zero records'
        assert manifest.get('readings') == readings, (
            f"Replay fixture was recorded with {{manifest.get('readings')}} readings "
            f"but this run requested {{readings}}"
        )
        for adapter in manifest['adapters']:
            expected_count = manifest['counts'][adapter]
            actual_count = len(adapter_records.get(adapter, []))
            assert actual_count == expected_count, f'Replay did not consume all {{adapter}} fixture entries'
    output = json.dumps({{'version': 2, 'readings': outputs}}, indent=2, sort_keys=True) + '\\n'
    Path({str(args.output)!r}).write_text(output)
'''
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Run a no-Agent check in record or replay mode.')
    parser.add_argument('--check-name', required=True)
    parser.add_argument('--check-class')
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--mode', choices=['record', 'replay'], required=True)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--readings', type=int, default=1)
    parser.add_argument('--replay-time', type=float, default=1_700_000_000.0)
    parser.add_argument('--reading-interval', type=float, default=15.0)
    parser.add_argument(
        '--adapters',
        default='all',
        help='Comma-separated replay adapters to install. Defaults to all adapters.',
    )
    args = parser.parse_args(argv)

    if args.readings < 1:
        parser.error('--readings must be >= 1')

    if args.adapters == 'all':
        args.adapters_tuple = None
    else:
        args.adapters_tuple = tuple(adapter.strip() for adapter in args.adapters.split(',') if adapter.strip())
        unknown = sorted(set(args.adapters_tuple) - set(ADAPTERS))
        if unknown:
            parser.error(f'unsupported replay adapter(s): {", ".join(unknown)}')

    args.fixture.parent.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    try:
        import pytest
    except Exception as e:
        print(f'pytest is required for check replay runner: {e}', file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / 'test_replay_check_runner.py'
        _write_pytest_file(test_file, args)
        return pytest.main(['-q', str(test_file)])


if __name__ == '__main__':
    raise SystemExit(main())
