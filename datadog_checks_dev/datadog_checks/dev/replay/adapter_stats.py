# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections import Counter
from typing import Any


def adapter_operation_name(adapter: str, record: dict[str, Any]) -> str:
    """Return a stable operation label for one replay adapter record.

    Protocol-specific adapters should prefer an explicit ``operation`` field in
    their fixture records. Older/simple adapters predate that convention, so the
    shared summary layer derives a useful low-cardinality operation name from
    adapter-specific stable fields instead of forcing every adapter fixture to
    change shape.
    """
    operation = record.get('operation')
    if isinstance(operation, str) and operation:
        return operation

    if adapter == 'requests':
        method = record.get('method')
        if isinstance(method, str) and method:
            return f'http.{method.upper()}'
        return 'http.request'

    if adapter == 'subprocess':
        return 'subprocess.get_subprocess_output'

    return f'{adapter}.operation'


def summarize_adapter_records(adapter_records: dict[str, list[dict[str, Any]]] | None) -> list[dict[str, Any]]:
    """Summarize replay adapter activity as a deterministic output collection.

    The summary is intentionally generic so integration-specific properties can
    make call-budget assertions without depending on private adapter internals.
    For example, a future Kafka property can assert that
    ``confluent-kafka/admin.describe_consumer_groups`` stays at zero by default,
    while DB integrations can assert bounded query counts with the same output
    shape.
    """
    if not adapter_records:
        return []

    rows: list[dict[str, Any]] = []
    for adapter, records in sorted(adapter_records.items()):
        operation_counts = Counter(adapter_operation_name(adapter, record) for record in records)
        rows.append(
            {
                'adapter': adapter,
                'operation': '*',
                'count': len(records),
            }
        )
        for operation, count in sorted(operation_counts.items()):
            rows.append(
                {
                    'adapter': adapter,
                    'operation': operation,
                    'count': count,
                }
            )
    return rows
