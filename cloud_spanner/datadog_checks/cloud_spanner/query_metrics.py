# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import math
import time

from datadog_checks.base import datadog_agent
from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import obfuscate_sql_with_metadata
from datadog_checks.base.utils.serialization import json

from .queries import QUERY_STATS_COLUMNS, QUERY_STATS_TOP_MINUTE

OBFUSCATE_OPTIONS = to_native_string(json.dumps({'return_json_metadata': True}))

if False:  # TYPE_CHECKING
    from .check import SpannerCheck


def _nan_to_zero(value) -> float:
    v = float(value) if value is not None else 0.0
    return 0.0 if math.isnan(v) else v


class SpannerQueryMetrics:
    def __init__(self, check: SpannerCheck):
        self._check = check
        self._config = check._config
        self._log = check.log

    def collect(self, client) -> None:
        if not self._config.query_metrics.enabled:
            return
        try:
            rows = self._collect_rows(client)
            if not rows:
                return
            self._emit_payload(rows)
        except Exception:
            self._log.exception("Unable to collect Spanner query metrics")

    def _collect_rows(self, client) -> list[dict]:
        instance = client.instance(self._config.instance_id)
        database = instance.database(self._config.database)
        with database.snapshot() as snapshot:
            result = snapshot.execute_sql(QUERY_STATS_TOP_MINUTE)
            return [self._parse_row(row) for row in result]

    def _parse_row(self, row) -> dict:
        raw = dict(zip(QUERY_STATS_COLUMNS, row))

        text = raw.get('text') or ''
        obfuscated = obfuscate_sql_with_metadata(text, OBFUSCATE_OPTIONS)
        obfuscated_query = obfuscated.get('query', text)
        query_signature = compute_sql_signature(obfuscated_query)

        interval_end = raw.get('interval_end')

        return {
            'database': self._config.database,
            'query_signature': query_signature,
            'text': obfuscated_query,
            'text_truncated': bool(raw.get('text_truncated', False)),
            'text_fingerprint': raw.get('text_fingerprint'),
            'query_type': raw.get('query_type', 'GLOBAL'),
            'request_tag': raw.get('request_tag') or '',
            'interval_end': interval_end.isoformat() if interval_end is not None else None,
            'execution_count': int(raw.get('execution_count') or 0),
            'avg_latency_seconds': float(raw.get('avg_latency_seconds') or 0),
            'avg_rows': float(raw.get('avg_rows') or 0),
            'avg_bytes': float(raw.get('avg_bytes') or 0),
            'avg_rows_scanned': float(raw.get('avg_rows_scanned') or 0),
            'avg_cpu_seconds': float(raw.get('avg_cpu_seconds') or 0),
            'all_failed_execution_count': int(raw.get('all_failed_execution_count') or 0),
            'all_failed_avg_latency_seconds': _nan_to_zero(raw.get('all_failed_avg_latency_seconds')),
            'cancelled_or_disconnected_execution_count': int(raw.get('cancelled_or_disconnected_execution_count') or 0),
            'timed_out_execution_count': int(raw.get('timed_out_execution_count') or 0),
        }

    def _emit_payload(self, rows: list[dict]) -> None:
        payload = {
            'host': self._check.reported_hostname,
            'database_instance': self._check.reported_hostname,
            'timestamp': time.time() * 1000,
            'min_collection_interval': self._config.query_metrics.collection_interval,
            'tags': self._config.tags,
            'cloud_metadata': self._check.cloud_metadata,
            'spanner_version': 'spanner',
            'ddagentversion': datadog_agent.get_version(),
            'service': self._config.service,
            'spanner_rows': rows,
        }
        self._check.database_monitoring_query_metrics(json.dumps(payload))
