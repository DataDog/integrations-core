# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here

HERE = get_here()


def register_metrics(fake_http_response, fixture_filename, prometheus_url, check_runs=1):
    """Serve the fixture to the SLI probe in `__init__`, then to the metrics, SLI and health endpoints per check run."""
    with open(os.path.join(HERE, 'fixtures', fixture_filename), 'rb') as f:
        content = f.read()
    sli_url = prometheus_url + '/slis'
    fake_http_response(sli_url, content, headers={'Content-Type': 'text/plain'})
    for _ in range(check_runs):
        for url in (prometheus_url, sli_url):
            fake_http_response(url, content, headers={'Content-Type': 'text/plain'})
        fake_http_response(prometheus_url.removesuffix('/metrics') + '/healthz')
