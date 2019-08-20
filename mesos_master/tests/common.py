# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev import get_here
from datadog_checks.utils.common import get_docker_hostname

HERE = get_here()
HOST = get_docker_hostname()
PORT = '5050'

INSTANCE = {'url': 'http://{}:{}'.format(HOST, PORT), 'tags': ['instance:mytag1']}

CHECK_NAME = "mesos_master"

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