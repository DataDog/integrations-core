# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Diff the metrics a live ClickHouse server emits against what the generator expects for that version."""

import argparse

import generate_metrics as gen
import requests

# Matches tests/common.py CONFIG.
DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 8123
DEFAULT_USER = 'datadog'
DEFAULT_PASSWORD = 'Datadog123!'

REQUIRED_TABLES = {
    'system.metrics': {
        'fetch': gen.fetch_current_metrics,
        'column': 'metric',
        'prefix': gen.PREFIX_CURRENT_METRICS,
    },
}


def query_live(host: str, port: int, user: str, password: str, sql: str) -> set[str]:
    resp = requests.post(
        f'http://{host}:{port}/',
        params={'query': sql},
        auth=(user, password),
        timeout=15,
    )
    resp.raise_for_status()
    return {line for line in resp.text.splitlines() if line}


def diff_version(version: str, host: str, port: int, user: str, password: str) -> dict[str, dict[str, set[str]]]:
    """Return, per required system table, the metric_name() sets that drift each way."""
    report: dict[str, dict[str, set[str]]] = {}
    for table, spec in REQUIRED_TABLES.items():
        expected = {m.metric_name() for m in spec['fetch'](version).values()}
        raw_names = query_live(host, port, user, password, f"SELECT {spec['column']} FROM {table}")
        emitted = {f"{spec['prefix']}.{name}" for name in raw_names}

        report[table] = {
            'declared_not_emitted': (expected - emitted) - set(gen.NEVER_REQUIRED),
            'emitted_not_generated': emitted - expected,
        }
    return report


def print_report(version: str, report: dict[str, dict[str, set[str]]]) -> tuple[set[str], set[str]]:
    """Print a per-table report; return the aggregated drift sets."""
    all_missing_required: set[str] = set()
    all_new_upstream: set[str] = set()

    print()
    print(f'=== Diff against {version} ===')
    for table, drift in report.items():
        missing = drift['declared_not_emitted']
        new_upstream = drift['emitted_not_generated']
        all_missing_required |= missing
        all_new_upstream |= new_upstream

        if not missing and not new_upstream:
            print(f'  {table}: in sync')
            continue

        print(f'  {table}:')
        if missing:
            print(f'    declared as required but NOT emitted ({len(missing)}):')
            for name in sorted(missing):
                print(f'      {name}')
        if new_upstream:
            print(f'    emitted but NOT generated ({len(new_upstream)}):')
            for name in sorted(new_upstream):
                print(f'      {name}')
    print()

    return all_missing_required, all_new_upstream


def print_suggestions(missing_required: set[str], new_upstream: set[str]) -> None:
    if not missing_required and not new_upstream:
        print('No drift: generated metrics match the live server(s).')
        return

    if missing_required:
        print('Suggested NEVER_REQUIRED additions (paste into generate_metrics.py):')
        print('NEVER_REQUIRED = {')
        for name in sorted(set(gen.NEVER_REQUIRED) | missing_required):
            print(f'    {name!r},')
        print('}')
        print()

    if new_upstream:
        print('New upstream metrics are emitted but not in the generated data.')
        print('Rerun the generator to pick them up:')
        print('    hatch run metrics:generate')
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--version',
        help='ClickHouse version to diff (must match the running server). Defaults to every entry in VERSIONS.',
    )
    parser.add_argument('--host', default=DEFAULT_HOST)
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    parser.add_argument('--user', default=DEFAULT_USER)
    parser.add_argument('--password', default=DEFAULT_PASSWORD)
    args = parser.parse_args()

    target_versions = [args.version] if args.version else gen.versions()

    missing_required: set[str] = set()
    new_upstream: set[str] = set()
    for version in target_versions:
        report = diff_version(version, args.host, args.port, args.user, args.password)
        version_missing, version_new = print_report(version, report)
        missing_required |= version_missing
        new_upstream |= version_new

    print_suggestions(missing_required, new_upstream)


if __name__ == '__main__':
    main()
