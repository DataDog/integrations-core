# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.utils.common import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))

# Networking
HOST = get_docker_hostname()

GITLAB_TEST_PASSWORD = "testroot"
GITLAB_LOCAL_PORT = 8086
GITLAB_LOCAL_PROMETHEUS_PORT = 8088

PROMETHEUS_ENDPOINT = "http://{}:{}/metrics".format(HOST, GITLAB_LOCAL_PROMETHEUS_PORT)
GITLAB_URL = "http://{}:{}".format(HOST, GITLAB_LOCAL_PORT)
GITLAB_TAGS = ['gitlab_host:{}'.format(HOST), 'gitlab_port:{}'.format(GITLAB_LOCAL_PORT)]

CUSTOM_TAGS = ['optional:tag1']

# Note that this is a subset of the ones defined in GitlabCheck
# When we stand up a clean test infrastructure some of those metrics might not
# be available yet, hence we validate a stable subset
ALLOWED_METRICS = [
    'process_max_fds',
    'process_open_fds',
    'process_resident_memory_bytes',
    'process_start_time_seconds',
    'process_virtual_memory_bytes'
]

CONFIG = {
    'init_config': {
        'allowed_metrics': ALLOWED_METRICS
    },
    'instances': [{
        'prometheus_endpoint': PROMETHEUS_ENDPOINT,
        'gitlab_url': GITLAB_URL,
        'disable_ssl_validation': True,
        'tags': list(CUSTOM_TAGS)
    }]
}

BAD_CONFIG = {
    'init_config': {
        'allowed_metrics': ALLOWED_METRICS
    },
    'instances': [{
        'prometheus_endpoint': 'http://{}:1234/metrics'.format(HOST),
        'gitlab_url': 'http://{}:1234/ci'.format(HOST),
        'disable_ssl_validation': True,
        'tags': list(CUSTOM_TAGS)
    }]
}
