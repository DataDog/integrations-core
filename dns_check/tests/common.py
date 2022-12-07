# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.docker import using_windows_containers
from datadog_checks.dev.utils import get_metadata_metrics

INSTANCE_INTEGRATION = {'name': 'datadog', 'hostname': 'www.datadoghq.com', 'nameserver': '8.8.8.8'}

CONFIG_SUCCESS = {
    'instances': [
        {'name': 'success', 'hostname': 'www.example.org', 'nameserver': '127.0.0.1'},
        {'name': 'cname', 'hostname': 'www.example.org', 'nameserver': '127.0.0.1', 'record_type': 'CNAME'},
        {
            'name': 'check_response_ip',
            'hostname': 'www.example.org',
            'nameserver': '127.0.0.1',
            'resolves_as': '127.0.0.2',
        },
        {
            'name': 'check_response_multiple_ips',
            'hostname': 'my.example.org',
            'nameserver': '127.0.0.1',
            'resolves_as': '127.0.0.2,127.0.0.3,127.0.0.4',
        },
        {
            'name': 'check_response_CNAME',
            'hostname': 'www.example.org',
            'nameserver': '127.0.0.1',
            'record_type': 'CNAME',
            'resolves_as': 'alias.example.org',
        },
    ]
}

CONFIG_SUCCESS_NXDOMAIN = {
    'name': 'nxdomain',
    'hostname': 'www.example.org',
    'nameserver': '127.0.0.1',
    'record_type': 'NXDOMAIN',
}

CONFIG_DEFAULT_TIMEOUT = {
    'init_config': {'default_timeout': 0.1},
    'instances': [{'name': 'default_timeout', 'hostname': 'www.example.org', 'nameserver': '127.0.0.1'}],
}

CONFIG_INSTANCE_TIMEOUT = {
    'name': 'instance_timeout',
    'hostname': 'www.example.org',
    'timeout': 0.1,
    'nameserver': '127.0.0.1',
}

CONFIG_INVALID = [
    # invalid hostname
    ({'name': 'invalid_hostname', 'hostname': 'example'}, "DNS resolution of example has failed"),
    # invalid nameserver
    (
        {'name': 'invalid_nameserver', 'hostname': 'www.example.org', 'nameserver': '0.0.0.0'},
        "DNS resolution of www.example.org timed out",
    ),
    # invalid record type
    (
        {'name': 'invalid_rcrd_type', 'hostname': 'www.example.org', 'record_type': 'FOO'},
        "DNS resolution of www.example.org has failed",
    ),
    # valid domain when NXDOMAIN is expected
    (
        {'name': 'valid_domain_for_nxdomain_type', 'hostname': 'example.com', 'record_type': 'NXDOMAIN'},
        "DNS resolution of example.com has failed",
    ),
]

E2E_METADATA = {'docker_platform': 'windows' if using_windows_containers() else 'linux'}


def _test_check(aggregator):
    aggregator.assert_metric('dns.response_time')
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
