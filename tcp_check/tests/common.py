# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.docker import using_windows_containers
from datadog_checks.tcp_check import TCPCheck

CHECK_NAME = "tcp_check"

INSTANCE = {'host': 'datadoghq.com', 'port': 80, 'timeout': 1.5, 'name': 'UpService', 'tags': ["foo:bar"]}

INSTANCE_MULTIPLE = {'multiple_ips': True}
INSTANCE_MULTIPLE.update(INSTANCE)

INSTANCE_IPV6 = {
    'host': 'ip-ranges.datadoghq.com',
    'port': 80,
    'timeout': 1.5,
    'name': 'UpService',
    'tags': ["foo:bar"],
    'multiple_ips': True,
}

INSTANCE_KO = {'host': '127.0.0.1', 'port': 65530, 'timeout': 1.5, 'name': 'DownService', 'tags': ["foo:bar"]}

E2E_METADATA = {'docker_platform': 'windows' if using_windows_containers() else 'linux'}


def _test_check(aggregator, addrs):
    common_tags = ['foo:bar', 'target_host:datadoghq.com', 'port:80', 'instance:UpService']
    for addr in addrs:
        tags = common_tags + ['address:{}'.format(addr)]
        aggregator.assert_metric('network.tcp.can_connect', value=1, tags=tags)
        aggregator.assert_service_check('tcp.can_connect', status=TCPCheck.OK, tags=tags)
    aggregator.assert_all_metrics_covered()
    assert len(aggregator.service_checks('tcp.can_connect')) == len(addrs)
