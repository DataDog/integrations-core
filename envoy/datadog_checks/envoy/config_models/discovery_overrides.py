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
# this override), which makes urlsplit(...).port raise ValueError instead of
# returning a port number. Treat that as "not a known admin port" rather than
# letting the exception abort candidate generation entirely.
ADMIN_PORTS = {8001, 9901}


def candidates(
    service: Service, default: Callable[[Service], Iterator[dict[str, Any]]]
) -> Iterator[dict[str, Any]]:
    for candidate in default(service):
        instance = candidate['instances'][0]
        try:
            port = urlsplit(instance['openmetrics_endpoint']).port
        except ValueError:
            port = None
        if port not in ADMIN_PORTS:
            instance['collect_server_info'] = False
        yield candidate
