# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
#!/usr/bin/env python3
"""Run HanaSchemaCollector in one mode (limited or unlimited) and print peak memory as JSON.

Invoked by benchmark.py as a subprocess so each mode gets a clean high-water mark.
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
import time
import tracemalloc
from resource import RUSAGE_SELF, getrusage

DATADOG_USER = "datadog"
DATADOG_PASSWORD = "Datadog9000"
HOST = "localhost"
PORT = 39019

MODES = {
    "limited": {"enabled": True, "max_tables": 300, "max_columns": 50},
    "unlimited": {"enabled": True, "max_tables": 10_000_000, "max_columns": 10_000_000},
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=list(MODES), required=True)
    parser.add_argument('--host', default=HOST)
    parser.add_argument('--port', type=int, default=PORT)
    args = parser.parse_args()

    from hdbcli.dbapi import Connection as HanaConnection

    from datadog_checks.sap_hana import SapHanaCheck

    instance = {
        'server': args.host,
        'port': args.port,
        'username': DATADOG_USER,
        'password': DATADOG_PASSWORD,
        'collect_schemas': MODES[args.mode],
    }
    check = SapHanaCheck('sap_hana', {}, [instance])
    check._conn = HanaConnection(address=args.host, port=args.port, user=DATADOG_USER, password=DATADOG_PASSWORD)

    payload_count = 0
    total_payload_bytes = 0

    def record_payload(raw: str) -> None:
        nonlocal payload_count, total_payload_bytes
        payload_count += 1
        total_payload_bytes += len(raw.encode())

    check.database_monitoring_metadata = record_payload
    check.histogram = lambda *a, **kw: None
    check.gauge = lambda *a, **kw: None

    gc.collect()
    tracemalloc.start()
    t0 = time.perf_counter()

    check._schema_collector.collect_schemas()

    duration_s = time.perf_counter() - t0
    peak_rss_kb = getrusage(RUSAGE_SELF).ru_maxrss
    _, tracemalloc_peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    result = {
        'mode': args.mode,
        'peak_rss_kb': peak_rss_kb,
        'tracemalloc_peak_bytes': tracemalloc_peak_bytes,
        'payloads': payload_count,
        'total_payload_bytes': total_payload_bytes,
        'duration_s': round(duration_s, 3),
    }
    print(json.dumps(result))


if __name__ == '__main__':
    sys.exit(main())
