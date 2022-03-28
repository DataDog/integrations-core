# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from sys import maxsize

import pytest
from packaging import version

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
HAPROXY_LEGACY = os.getenv('HAPROXY_LEGACY')
HAPROXY_VERSION_RAW = os.getenv('HAPROXY_VERSION', 'latest')

HAPROXY_VERSION_IS_LATEST = HAPROXY_VERSION_RAW.endswith('latest')
if HAPROXY_VERSION_IS_LATEST:
    HAPROXY_VERSION = version.parse(str(maxsize))
else:
    HAPROXY_VERSION = version.parse(HAPROXY_VERSION_RAW)
ENDPOINT_PROMETHEUS = 'http://{}:8404/metrics'.format(HOST)

INSTANCE = {'use_prometheus': True, 'prometheus_url': ENDPOINT_PROMETHEUS}
INSTANCEV2 = {'use_openmetrics': True, 'openmetrics_endpoint': ENDPOINT_PROMETHEUS}

requires_new_environment = pytest.mark.skipif(HAPROXY_LEGACY != 'false', reason='Requires prometheus environment')
requires_static_version = pytest.mark.skipif(
    HAPROXY_VERSION_IS_LATEST, reason='Version `latest` is ever-changing, skipping'
)
