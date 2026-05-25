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

from datadog_checks.dev.replay.adapters import install_replay_adapter
from datadog_checks.dev.replay.output import serialize_aggregator
from datadog_checks.dev.replay.pytest import run_check_instances


def test_replay_check_runner(monkeypatch, aggregator, datadog_agent, dd_run_check):
    config = json.loads(Path({str(args.config)!r}).read_text())
    instances = config.get('instances', [config])
    fixture = Path({str(args.fixture)!r})
    install_replay_adapter(monkeypatch, {args.adapter!r}, {args.mode!r}, fixture)

    run_check_instances({args.check_class!r}, instances, dd_run_check, {args.check_name!r})
    output = json.dumps(serialize_aggregator(aggregator, datadog_agent), indent=2, sort_keys=True) + '\\n'
    Path({str(args.output)!r}).write_text(output)
'''
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Run a no-Agent check in record or replay mode.')
    parser.add_argument('--check-name', required=True)
    parser.add_argument('--check-class')
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--mode', choices=['record', 'replay'], required=True)
    parser.add_argument('--adapter', choices=ADAPTERS, default='requests')
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)

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
