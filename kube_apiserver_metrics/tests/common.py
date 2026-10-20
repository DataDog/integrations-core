# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

APISERVER_INSTANCE_BEARER_TOKEN = "XXX"
HERE = os.path.dirname(os.path.abspath(__file__))

PROMETHEUS_URL = 'https://localhost:443/metrics'
SLI_URL = PROMETHEUS_URL + '/slis'


def register_metrics(fake_http_response, file_path, check_runs=1):
    """Serve the fixture to the SLI probe in `__init__`, then to both endpoints on each check run."""
    with open(file_path, 'rb') as f:
        content = f.read()
    for url in [SLI_URL] + [PROMETHEUS_URL, SLI_URL] * check_runs:
        fake_http_response(url, content, headers={'Content-Type': 'text/plain'})
