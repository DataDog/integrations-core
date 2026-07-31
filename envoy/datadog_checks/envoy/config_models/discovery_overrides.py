# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from urllib.parse import urlsplit

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
ADMIN_PORTS = {8001, 9901}


def candidates(service, default):
    for candidate in default(service):
        instance = candidate['instances'][0]
        if urlsplit(instance['openmetrics_endpoint']).port not in ADMIN_PORTS:
            instance['collect_server_info'] = False
        yield candidate
