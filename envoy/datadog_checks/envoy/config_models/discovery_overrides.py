# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from urllib.parse import urlsplit

# Override the generated discovery candidates() for this integration.
#
# candidate_ports() yields every exposed port, hinted ports first, so the
# generated stats_url candidate would otherwise be probed against any port on
# the container. The legacy check also calls /server_info before scraping
# /stats, so letting that run against arbitrary ports risks hitting an
# unrelated upstream and misidentifying it as Envoy's admin endpoint. Restrict
# stats_url to the hinted admin ports only; openmetrics_endpoint keeps the
# default fallback across all candidate ports.
#
# Both EnvoyCheckV2.check() and the legacy check call _collect_metadata() before
# scraping metrics, unconditionally, regardless of dispatch mode. It defaults to
# on (collect_server_info defaults to True) and hits <base_url>/server_info,
# which for openmetrics_endpoint candidates is derived straight from the
# discovered port. So a fallback openmetrics_endpoint candidate on a non-admin
# port carries the same misidentification risk as stats_url did — just via
# metadata collection instead of the main scrape. Disable collect_server_info on
# those fallback candidates rather than dropping them, since the OpenMetrics
# scrape itself is still safe to attempt on any port.
#
# Known limitation: this only discovers the legacy /stats endpoint when the
# admin port matches one of the hinted ports used by this integration's
# discovery strategy (8001, the port used in Datadog's own example configs and
# test fixtures, and 9901, the port commonly used in Envoy documentation
# examples). Envoy deployments exposing admin on a different port still
# require a hand-written static config, and won't get version metadata
# collection on their openmetrics_endpoint candidate either.
ADMIN_PORTS = {8001, 9901}


def candidates(service, default):
    for candidate in default(service):
        instance = candidate['instances'][0]
        if 'stats_url' in instance:
            if urlsplit(instance['stats_url']).port not in ADMIN_PORTS:
                continue
        elif 'openmetrics_endpoint' in instance:
            if urlsplit(instance['openmetrics_endpoint']).port not in ADMIN_PORTS:
                instance['collect_server_info'] = False
        yield candidate
