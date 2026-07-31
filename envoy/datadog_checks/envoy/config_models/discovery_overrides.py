# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

from datadog_checks.base.utils.discovery import Service


def candidates(service: Service, default: Callable[[Service], Iterator[dict[str, Any]]]) -> Iterator[dict[str, Any]]:
    # Bracket unbracketed IPv6 hosts; port hints never confirm admin status, so server_info collection stays off.
    bracketed_host = f'[{service.host}]' if ':' in service.host else service.host
    for candidate in default(service):
        instance = candidate['instances'][0]
        if bracketed_host != service.host:
            instance['openmetrics_endpoint'] = instance['openmetrics_endpoint'].replace(service.host, bracketed_host, 1)
        instance['collect_server_info'] = False
        yield candidate
