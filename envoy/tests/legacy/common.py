# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.dev import get_docker_hostname

FLAVOR = os.getenv('FLAVOR', 'api_v3')

HOST = get_docker_hostname()
PORT = '8001'
INSTANCES = {
    'main': {'stats_url': 'http://{}:{}/stats'.format(HOST, PORT)},
    'included_metrics': {
        'stats_url': 'http://{}:{}/stats'.format(HOST, PORT),
        'metric_whitelist': [r'envoy\.cluster\..*'],
    },
    'excluded_metrics': {
        'stats_url': 'http://{}:{}/stats'.format(HOST, PORT),
        'metric_blacklist': [r'envoy\.cluster\..*'],
    },
    'included_excluded_metrics': {
        'stats_url': 'http://{}:{}/stats'.format(HOST, PORT),
        'included_metrics': [r'envoy\.cluster\.'],
        'excluded_metrics': [r'envoy\.cluster\.out\.'],
    },
    'include_exclude_metrics': {
        'stats_url': 'http://{}:{}/stats'.format(HOST, PORT),
        'include_metrics': [r'envoy\.cluster\.'],
        'exclude_metrics': [r'envoy\.cluster\.out\.'],
    },
    'collect_server_info': {
        'stats_url': 'http://{}:{}/stats'.format(HOST, PORT),
        'collect_server_info': 'false',
    },
}
ENVOY_VERSION = os.getenv('ENVOY_VERSION')

EXT_METRICS = [
    "envoy.cluster.ext_authz.denied",
    "envoy.cluster.ext_authz.disabled",
    "envoy.cluster.ext_authz.error",
    "envoy.cluster.ext_authz.failure_mode_allowed",
    "envoy.cluster.ext_authz.ok",
]

LOCAL_RATE_LIMIT_METRICS = [
    "envoy.http_local_rate_limit.enabled",
    "envoy.http_local_rate_limit.enforced",
    "envoy.http_local_rate_limit.rate_limited",
    "envoy.http_local_rate_limit.ok",
]

RATE_LIMIT_STAT_PREFIX_TAG = ['stat_prefix:http_local_rate_limiter', 'stat_prefix:foo_buz_112']

CONNECTION_LIMIT_METRICS = [
    "envoy.connection_limit.active_connections",
    "envoy.connection_limit.limited_connections",
]

CONNECTION_LIMIT_STAT_PREFIX_TAG = ['stat_prefix:ingress_http']

RBAC_METRICS = [
    "envoy.http.rbac.allowed",
    "envoy.http.rbac.denied",
    "envoy.http.rbac.shadow_allowed",
    "envoy.http.rbac.shadow_denied",
]
