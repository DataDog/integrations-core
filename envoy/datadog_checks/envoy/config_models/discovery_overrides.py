# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any
from urllib.parse import urlsplit

from datadog_checks.base.utils.discovery import Service

# Override the generated discovery candidates() for this integration.
#
# candidate_ports() yields every exposed port, hinted ports first, then falls back
# to every other exposed port on the container, so a candidate can be generated for
# an arbitrary, unrelated port. EnvoyCheckV2.check() always calls _collect_metadata()
# before scraping, which hits <base_url>/server_info (collect_server_info defaults
# to True) derived straight from the discovered port. Letting that run against an
# arbitrary port risks hitting an unrelated upstream and misidentifying it as Envoy.
# Disable collect_server_info on fallback candidates outside the two known admin
# ports rather than dropping them, since the OpenMetrics scrape itself is still
# safe to attempt on any port.
#
# service.host is interpolated unbracketed for IPv6 literals by the generated
# template (a pre-existing gap in the shared discovery templating, not specific to
# this override), which produces an invalid URL like http://fd00::1:8080/... and
# makes urlsplit(...).port raise ValueError instead of returning a port number.
# service.host itself is available here unmangled, so repair the URL by bracketing
# it before parsing, rather than just swallowing the parse error.
ADMIN_PORTS = {8001, 9901}


def candidates(service: Service, default: Callable[[Service], Iterator[dict[str, Any]]]) -> Iterator[dict[str, Any]]:
    bracketed_host = f'[{service.host}]' if ':' in service.host else service.host
    for candidate in default(service):
        instance = candidate['instances'][0]
        if bracketed_host != service.host:
            instance['openmetrics_endpoint'] = instance['openmetrics_endpoint'].replace(service.host, bracketed_host, 1)
        try:
            port = urlsplit(instance['openmetrics_endpoint']).port
        except ValueError:
            port = None
        if port not in ADMIN_PORTS:
            instance['collect_server_info'] = False
        yield candidate
