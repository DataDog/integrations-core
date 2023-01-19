# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from collections import defaultdict

from datadog_checks.cloudera.metrics import NATIVE_METRICS, TIMESERIES_METRICS
from datadog_checks.dev import get_docker_hostname, get_here

HOST = get_docker_hostname()
PORT = 7180

INSTANCE = {
    'api_url': 'http://localhost:8080/api/v48/',
    'tags': ['test1'],
}

INSTANCE_BAD_URL = {
    'api_url': 'http://bad_host:8080/api/v48/',
    'tags': ['test1'],
}

INSTANCE_AUTODISCOVER_CLUSTERS_INCLUDE_NOT_ARRAY = {
    'api_url': 'http://localhost:8080/api/v48/',
    'tags': ['test1'],
    'clusters': {
        'include': {
            '^cluster.*',
        },
    },
}


INSTANCE_AUTODISCOVER_INCLUDE_WITH_ONE_ENTRY_DICT = {
    'api_url': 'http://localhost:8080/api/v48/',
    'tags': ['test1'],
    'clusters': {
        'include': [
            {
                '^cluster.*': {'hosts': {}},
            },
        ],
    },
}

INSTANCE_AUTODISCOVER_INCLUDE_WITH_TWO_ENTRIES_DICT = {
    'api_url': 'http://localhost:8080/api/v48/',
    'tags': ['test1'],
    'clusters': {
        'include': [
            {
                '^cluster.*': {'hosts': {}},
                '^tmp.*': {'hosts': {}},
            },
        ],
    },
}

INSTANCE_AUTODISCOVER_INCLUDE_WITH_STR = {
    'api_url': 'http://localhost:8080/api/v48/',
    'tags': ['test1'],
    'clusters': {
        'include': [
            '^cluster.*',
        ],
    },
}

INSTANCE_AUTODISCOVER_EXCLUDE = {
    'api_url': 'http://localhost:8080/api/v48/',
    'tags': ['test1'],
    'clusters': {
        'include': [
            {
                '.*': {},
            },
        ],
        'exclude': ['^tmp.*'],
    },
}

INIT_CONFIG = {
    'workload_username': '~',
    'workload_password': '~',
}

HERE = get_here()
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

CAN_CONNECT_TAGS = [
    'api_url:http://localhost:8080/api/v48/',
    'test1',
]
CLUSTER_1_HEALTH_TAGS = [
    '_cldr_cb_clustertype:Data Hub',
    '_cldr_cb_origin:cloudbreak',
    'cloudera_cluster:cluster_1',
    'test1',
]
CLUSTER_TMP_HEALTH_TAGS = [
    '_cldr_cb_clustertype:Data Hub',
    '_cldr_cb_origin:cloudbreak',
    'cloudera_cluster:tmp_cluster',
    'test1',
]


def merge_dicts(d1, d2):
    merged_dict = defaultdict(list)
    for d in (d1, d2):
        for key, value in d.items():
            merged_dict[key] += value
    return merged_dict


METRICS = merge_dicts(NATIVE_METRICS, TIMESERIES_METRICS)
