# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here

HERE = get_here()

PROMETHEUS_URL = 'https://localhost:443/metrics'
HEALTH_URL = 'https://localhost:443/livez'


def register_metrics(fake_http_response, fixture_filename, check_runs=1):
    """Serve the fixture and a healthy health endpoint for each check run."""
    with open(os.path.join(HERE, 'fixtures', fixture_filename), 'rb') as f:
        content = f.read()
    for _ in range(check_runs):
        fake_http_response(PROMETHEUS_URL, content, headers={'Content-Type': 'text/plain'})
        fake_http_response(HEALTH_URL)
