# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
#!/usr/bin/env python3
"""Orchestrate limited vs unlimited schema collection runs and compare peak memory."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

RESULTS_DIR = os.path.join(os.path.dirname(__file__), 'results')
RESULTS_FILE = os.path.join(RESULTS_DIR, 'benchmark_results.txt')
RUN_COLLECTOR = os.path.join(os.path.dirname(__file__), 'run_collector.py')
SETUP_DATABASE = os.path.join(os.path.dirname(__file__), 'setup_database.py')

HOST = 'localhost'
PORT = 39019


def wait_for_hana(host: str, port: int, timeout: int = 600) -> None:
    print(f'Waiting for SAP HANA at {host}:{port} (up to {timeout}s)...', flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            from hdbcli.dbapi import Connection as HanaConnection

            conn = HanaConnection(address=host, port=port, user='system', password='Admin1337')
            conn.close()
            print('HANA is ready.', flush=True)
            return
        except Exception:
            time.sleep(5)
    print('ERROR: HANA did not become ready in time.', file=sys.stderr)
    sys.exit(1)


def run_mode(python: str, mode: str, host: str, port: int) -> dict:
    print(f'Running mode={mode}...', flush=True)
    result = subprocess.run(
        [python, RUN_COLLECTOR, '--mode', mode, '--host', host, '--port', str(port)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f'ERROR running mode={mode}:\n{result.stderr}', file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout.strip())


def mib(value_bytes: int) -> str:
    return f'{value_bytes / 1024 / 1024:.1f} MiB'


def build_report(limited: dict, unlimited: dict) -> str:
    rss_ratio = unlimited['peak_rss_kb'] / max(limited['peak_rss_kb'], 1)
    lines = [
        'SAP HANA Schema Collection Memory Benchmark',
        '=' * 60,
        '',
        f"{'Mode':<12} {'Peak RSS':>12} {'Tracemalloc':>14} {'Payloads':>10} {'Payload bytes':>15} {'Duration':>10}",
        '-' * 75,
    ]
    for r in (limited, unlimited):
        lines.append(
            f"{r['mode']:<12}"
            f" {mib(r['peak_rss_kb'] * 1024):>12}"
            f" {mib(r['tracemalloc_peak_bytes']):>14}"
            f" {r['payloads']:>10}"
            f" {r['total_payload_bytes']:>15,}"
            f" {r['duration_s']:>9.1f}s"
        )
    lines += [
        '',
        f"Memory reduction: {rss_ratio:.1f}x less peak RSS with limits enabled",
        "  limited  : max_tables=300, max_columns=50",
        "  unlimited: max_tables=10_000_000, max_columns=10_000_000",
        '',
    ]
    return '\n'.join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description='Run the schema collection memory benchmark.')
    parser.add_argument('--skip-setup', action='store_true', help='Skip database setup (schema already populated).')
    parser.add_argument('--python', default=sys.executable, help='Python interpreter for child runs.')
    parser.add_argument('--host', default=HOST)
    parser.add_argument('--port', type=int, default=PORT)
    args = parser.parse_args()

    wait_for_hana(args.host, args.port)

    if not args.skip_setup:
        print('Running database setup...', flush=True)
        result = subprocess.run(
            [args.python, SETUP_DATABASE, '--host', args.host, '--port', str(args.port)],
            check=True,
        )
        _ = result

    limited = run_mode(args.python, 'limited', args.host, args.port)
    unlimited = run_mode(args.python, 'unlimited', args.host, args.port)

    report = build_report(limited, unlimited)
    print(report)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(RESULTS_FILE, 'w') as f:
        f.write(report)
    print(f'Results written to {RESULTS_FILE}')


if __name__ == '__main__':
    sys.exit(main())
