# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import get_here
from datadog_checks.dev.utils import running_on_windows_ci
from datadog_checks.base.utils.common import get_docker_hostname

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
    'mesos.role.frameworks.count',
    'mesos.cluster.total_frameworks',
    'mesos.role.weight',
]
