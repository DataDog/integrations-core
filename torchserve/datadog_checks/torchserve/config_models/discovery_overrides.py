# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from datadog_checks.base.utils.discovery import Service

# TorchServe exposes its Inference (8080/7070 gRPC), Management (8081/7071 gRPC), and
# OpenMetrics (8082) APIs as separate ports on one container. `candidate_ports()`
# yields the hinted 8082 port first, then falls back to every other exposed port, so
# the generated `from_ports` strategy would also probe the other four as OpenMetrics
# endpoints; probing the gRPC ports over HTTP logs container-side errors. Drop those
# known non-metrics ports, but keep every other port as a fallback candidate in case
# OpenMetrics is exposed on a custom port.
NON_METRICS_PORTS = frozenset({8080, 8081, 7070, 7071})


def candidates(service: Service, default) -> Iterator[dict[str, Any]]:
    excluded_endpoints = {f'http://{service.host}:{port}/metrics' for port in NON_METRICS_PORTS}
    for candidate in default(service):
        endpoint = candidate['instances'][0].get('openmetrics_endpoint')
        if endpoint not in excluded_endpoints:
            yield candidate
