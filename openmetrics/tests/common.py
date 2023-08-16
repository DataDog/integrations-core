# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.dev import get_docker_hostname, get_here

CHECK_NAME = 'openmetrics'

HERE = get_here()

HOST = get_docker_hostname()

INSTANCE = {
    'prometheus_url': 'http://{}:9090/metrics'.format(HOST),
    'namespace': 'openmetrics',
    'metrics': [
        {'prometheus_target_interval_length_seconds': 'target_interval_seconds'},  # summary
        {'prometheus_http_request_duration_seconds': 'http_req_duration_seconds'},  # histogram
        'go_memstats_mallocs_total',  # counter
        'go_memstats_alloc_bytes',  # gauge
    ],
}
