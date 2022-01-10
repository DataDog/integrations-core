# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
MOCKED_INSTANCE = {
    'url': 'mocked',
    'username': 'datadog',
    'password': 'password',
    'tags': ['foo:bar'],
}
E2E_INSTANCE = [
    {
        'url': 'http://{}:8081'.format(HOST),
        'username': 'datadog',
        'password': 'password',
    },
    {
        'url': 'http://{}:8082'.format(HOST),
        'username': 'datadog',
        'password': 'password',
    },
    {
        'url': 'http://{}:8083'.format(HOST),
        'username': 'datadog',
        'password': 'password',
    },
]
COMPOSE_FILE = os.path.join(HERE, 'compose', 'docker-compose.yaml')

SESSION_MASTER = {
    'Status': 'Success',
    'Value': 'OpaqueRef:c908ccc4-4355-4328-b07d-c85dc7242b03',
}
SESSION_SLAVE = {
    'Status': 'Failure',
    'ErrorDescription': ['HOST_IS_SLAVE', '192.168.101.102'],
}
SESSION_ERROR = {
    'Status': 'Failure',
    'ErrorDescription': ['SESSION_AUTHENTICATION_FAILED'],
}

SERVER_TYPE_SESSION_MAP = {
    'master': SESSION_MASTER,
    'slave': SESSION_SLAVE,
    'error': SESSION_ERROR,
}


def mocked_xenserver(server_type):
    xenserver = mock.MagicMock()
    xenserver.session.login_with_password.return_value = SERVER_TYPE_SESSION_MAP.get(server_type, {})
    return xenserver


def _assert_standalone_metrics(aggregator, custom_tags, count=1):
    host_tag = 'citrix_hypervisor_host:4cff6b2b-a236-42e0-b388-c78a413f5f46'
    vm_tag = 'citrix_hypervisor_vm:cc11e6e9-5071-4707-830a-b87e5618e874'
    METRICS = [
        ('host.cache_hits', [host_tag, 'cache_sr:e358b352-5dda-5261-6a91-f7b73e2bcbae']),
        ('host.cache_misses', [host_tag, 'cache_sr:e358b352-5dda-5261-6a91-f7b73e2bcbae']),
        ('host.cache_size', [host_tag, 'cache_sr:e358b352-5dda-5261-6a91-f7b73e2bcbae']),
        ('host.cache_hits', [host_tag, 'cache_sr:70039e15-abfe-85f7-a703-798b05110ee8']),
        ('host.cache_misses', [host_tag, 'cache_sr:70039e15-abfe-85f7-a703-798b05110ee8']),
        ('host.cache_size', [host_tag, 'cache_sr:70039e15-abfe-85f7-a703-798b05110ee8']),
        ('host.pif.rx', [host_tag, 'interface:aggr']),
        ('host.pif.tx', [host_tag, 'interface:aggr']),
        ('host.pif.rx', [host_tag, 'interface:eth0']),
        ('host.pif.tx', [host_tag, 'interface:eth0']),
        ('host.pif.rx', [host_tag, 'interface:eth1']),
        ('host.pif.tx', [host_tag, 'interface:eth1']),
        ('host.cpu', [host_tag, 'cpu_id:0']),
        ('host.cpu', [host_tag, 'cpu_id:0-C0']),
        ('host.cpu', [host_tag, 'cpu_id:0-C1']),
        ('host.memory.free_kib', [host_tag]),
        ('host.memory.reclaimed', [host_tag]),
        ('host.memory.reclaimed_max', [host_tag]),
        ('host.memory.total_kib', [host_tag]),
        ('host.pool.session_count', [host_tag]),
        ('host.pool.task_count', [host_tag]),
        ('host.xapi.allocation_kib', [host_tag]),
        ('host.xapi.free_memory_kib', [host_tag]),
        ('host.xapi.live_memory_kib', [host_tag]),
        ('host.xapi.memory_usage_kib', [host_tag]),
        ('host.xapi.open_fds', [host_tag]),
        ('vm.cpu', [vm_tag, 'cpu_id:0']),
        ('vm.memory', [vm_tag]),
    ]

    for m in METRICS:
        aggregator.assert_metric('citrix_hypervisor.{}'.format(m[0]), tags=m[1] + custom_tags, count=count)
