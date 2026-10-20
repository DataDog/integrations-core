# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here

HERE = get_here()

PROMETHEUS_URL = 'http://localhost:10251/metrics'
SLI_URL = PROMETHEUS_URL + '/slis'
HEALTH_URL = 'http://localhost:10251/healthz'


def register_metrics(fake_http_response, fixture_filename, check_runs=1):
    """Serve the fixture to the SLI probe in `__init__`, then to the metrics, SLI and health endpoints per check run."""
    with open(os.path.join(HERE, 'fixtures', fixture_filename), 'rb') as f:
        content = f.read()
    fake_http_response(SLI_URL, content, headers={'Content-Type': 'text/plain'})
    for _ in range(check_runs):
        for url in (PROMETHEUS_URL, SLI_URL):
            fake_http_response(url, content, headers={'Content-Type': 'text/plain'})
        fake_http_response(HEALTH_URL)
