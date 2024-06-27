# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.base.utils.common import get_docker_hostname
from datadog_checks.dev import get_here
from datadog_checks.dev.utils import running_on_windows_ci

not_windows_ci = pytest.mark.skipif(running_on_windows_ci(), reason='Test cannot be run on Windows CI')

HERE = get_here()
HOST = get_docker_hostname()
PORT = '5050'

INSTANCE = {'url': 'http://{}:{}'.format(HOST, PORT), 'tags': ['instance:mytag1']}

BAD_INSTANCE = {'url': 'http://localhost:9999', 'tasks': ['hello']}

CHECK_NAME = "mesos_master"

FIXTURE_DIR = os.path.join(HERE, 'fixtures')

MESOS_MASTER_VERSION = os.getenv('MESOS_MASTER_VERSION')

BASIC_METRICS = [
    'mesos.registrar.queued_operations',
    'mesos.registrar.registry_size_bytes',
    'mesos.registrar.state_fetch_ms',
    'mesos.registrar.state_store_ms',
    'mesos.stats.system.cpus_total',
    'mesos.stats.system.load_15min',
    'mesos.stats.system.load_1min',
    'mesos.stats.system.load_5min',
    'mesos.stats.system.mem_free_bytes',
    'mesos.stats.system.mem_total_bytes',
    'mesos.stats.elected',
    'mesos.stats.uptime_secs',
    'mesos.cluster.total_frameworks',
]

# With github actions updating its runner machine's docker to v26 not all versions of
#   mesos-master docker images were available, so we had to limit the versions to test
#   against. This results in some metrics not being available in the docker image used
#   for testing. Hence the following metrics are marked as optional.
OPTIONAL_METRICS = [
    'mesos.role.frameworks.count',
    'mesos.role.weight',
    'mesos.role.mem',
    'mesos.role.disk',
    'mesos.role.cpu',
]
