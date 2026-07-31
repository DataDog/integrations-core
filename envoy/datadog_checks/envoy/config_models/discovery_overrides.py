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
# Known limitation: this only discovers the legacy /stats endpoint when the
# admin port matches one of the hinted ports used by this integration's
# discovery strategy (8001, the port used in Datadog's own example configs and
# test fixtures, and 9901, the port commonly used in Envoy documentation
# examples). Envoy deployments exposing admin on a different port still
# require a hand-written static config.
ADMIN_PORTS = {8001, 9901}


def candidates(service, default):
    for candidate in default(service):
        instance = candidate['instances'][0]
        if 'stats_url' in instance and urlsplit(instance['stats_url']).port not in ADMIN_PORTS:
            continue
        yield candidate
