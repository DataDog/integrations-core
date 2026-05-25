#!/usr/bin/env python3
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Build a replay-PBT GitHub Actions matrix.

This intentionally reuses the existing CI matrix script so replay-PBT targets
match the integration E2E envs that normal CI knows how to run. The output is a
JSON list suitable for `matrix.include`.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(REPO_ROOT / 'ddev' / 'src' / 'ddev' / 'utils' / 'scripts'))

from ci_matrix import construct_job_matrix, get_all_targets, get_changed_targets  # noqa: E402


def slug(value: str) -> str:
    value = re.sub(r'[^A-Za-z0-9_.-]+', '-', value).strip('-')
    return value or 'none'


def is_safe_path_component(value: str) -> bool:
    return value not in {'', '.', '..'} and '/' not in value and '\\' not in value and '\x00' not in value


def git(*args: str) -> str:
    return subprocess.check_output(['git', '-C', str(REPO_ROOT), *args], text=True).strip()


def latest_integration_tag(integration: str) -> str | None:
    tags = git('tag', '--list', f'{integration}-*', '--sort=-v:refname').splitlines()
    return tags[0] if tags else None


def target_ref_head(target_ref: str) -> str:
    return git('rev-parse', target_ref)


def has_python_check(integration: str) -> bool:
    package_dir = REPO_ROOT / integration / 'datadog_checks' / integration
    if not package_dir.is_dir():
        return False

    for path in package_dir.glob('*.py'):
        if path.name in {'__about__.py'}:
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
        if re.search(r'^class\s+\w*Check\b', text, flags=re.MULTILINE):
            return True
    return False


def load_cached_targets() -> set[tuple[str, str]]:
    cached: set[tuple[str, str]] = set()
    replay_root = REPO_ROOT / '.ddev' / 'replay'
    if not replay_root.is_dir():
        return cached

    for refs_file in replay_root.glob('*/*/*/refs.json'):
        cache_dir = refs_file.parent
        if cache_dir.name == 'latest':
            continue
        try:
            status = json.loads((cache_dir / 'run_status.json').read_text())
            diff = json.loads((cache_dir / 'diff.json').read_text())
        except Exception:
            continue
        if status.get('comparable') is True and diff.get('changed') is False:
            rel = cache_dir.relative_to(replay_root)
            cached.add((rel.parts[0], rel.parts[1]))
    return cached


def build_targets(mode: str, ref: str) -> list[str]:
    if mode in {'all-declared', 'all-cached'}:
        return get_all_targets(REPO_ROOT)
    if mode == 'changed':
        return get_changed_targets(REPO_ROOT, ref=ref, exact=False, local=False, verbose=False)
    raise ValueError(f'unsupported mode: {mode}')


def main() -> None:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--mode', choices=['all-declared', 'all-cached', 'changed'], default='all-declared')
    parser.add_argument('--ref', default='origin/master', help='Base ref for --mode changed')
    parser.add_argument('--target-ref', default='HEAD')
    parser.add_argument('--readings', default='2')
    parser.add_argument('--max-targets', type=int, default=200)
    parser.add_argument('--allow-truncation', action='store_true')
    parser.add_argument('--shard-index', type=int, default=0)
    parser.add_argument('--shard-count', type=int, default=1)
    parser.add_argument('--platform', default='linux')
    args = parser.parse_args()

    targets = build_targets(args.mode, args.ref)
    normal_matrix = construct_job_matrix(REPO_ROOT, targets)
    cached_targets = load_cached_targets() if args.mode == 'all-cached' else None
    target_head = target_ref_head(args.target_ref)

    replay_matrix = []
    for job in normal_matrix:
        integration = job.get('target')
        environment = job.get('target-env')
        platform = job.get('platform')
        if not integration or not environment:
            continue
        if not is_safe_path_component(integration) or not is_safe_path_component(environment):
            raise ValueError(f'Unsafe replay-PBT target path component: {integration!r}:{environment!r}')
        if platform != args.platform:
            continue
        if integration in {'ddev', 'datadog_checks_base', 'datadog_checks_dev', 'datadog_checks_downloader'}:
            continue
        if not has_python_check(integration):
            continue
        if cached_targets is not None and (integration, environment) not in cached_targets:
            continue

        fixture_ref = latest_integration_tag(integration) or args.target_ref
        replay_matrix.append(
            {
                'name': f'{integration}:{environment}',
                'integration': integration,
                'environment': environment,
                'fixture_ref': fixture_ref,
                'target_ref': args.target_ref,
                'target_head': target_head,
                'readings': args.readings,
                'artifact_slug': slug(f'{integration}-{environment}'),
                'cache_key': 'replay-pbt-v4-'
                f'{slug(integration)}-{slug(environment)}-readings{slug(args.readings)}-fixture-{slug(fixture_ref)}'
                '-adapters-notcp',
            }
        )

    if args.shard_count < 1:
        raise ValueError('--shard-count must be >= 1')
    if args.shard_index < 0 or args.shard_index >= args.shard_count:
        raise ValueError('--shard-index must satisfy 0 <= index < count')

    replay_matrix = [row for index, row in enumerate(replay_matrix) if index % args.shard_count == args.shard_index]
    total = len(replay_matrix)
    if total > args.max_targets and not args.allow_truncation:
        required_shards = math.ceil(total / args.max_targets)
        raise SystemExit(
            f'Replay PBT selected {total} targets after sharding, but max_targets={args.max_targets}. '\
            'No matrix was emitted because truncation is disabled. '\
            f'Use shard_count>={required_shards} and dispatch every shard_index, increase max_targets, '\
            'or pass --allow-truncation for an intentional partial run.'
        )

    if total > args.max_targets:
        print(
            f'WARNING: truncating replay-PBT matrix from {total} to {args.max_targets} targets', file=sys.stderr
        )
        replay_matrix = replay_matrix[: args.max_targets]

    print(json.dumps(replay_matrix, separators=(',', ':')))
    print(f'Replay PBT targets after sharding before cap: {total}', file=sys.stderr)
    print(f'Replay PBT targets emitted: {len(replay_matrix)}', file=sys.stderr)


if __name__ == '__main__':
    main()
