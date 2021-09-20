# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.base import is_affirmative
from datadog_checks.citrix_hypervisor import CitrixHypervisorCheck
from datadog_checks.dev.utils import get_metadata_metrics

METRICS = [
    'host.cache_hits',
    'host.cache_misses',
    'host.cache_size',
    'host.cache_hits',
    'host.cache_misses',
    'host.cache_size',
    'host.cpu',
    'host.memory.free_kib',
    'host.memory.reclaimed',
    'host.memory.reclaimed_max',
    'host.memory.total_kib',
    'host.pif.rx',
    'host.pif.tx',
    'host.pool.session_count',
    'host.pool.task_count',
    'host.xapi.allocation_kib',
    'host.xapi.free_memory_kib',
    'host.xapi.live_memory_kib',
    'host.xapi.memory_usage_kib',
    'host.xapi.open_fds',
    'vm.cpu',
    'vm.memory',
]


def test_lab(aggregator, dd_run_check):
    """
    This test is intended to be run manually to connect to a real vSphere Instance

    It's useful for:
    - QA/testing the integration with real Citrix Hypervisor instances
    - using a debugger to inspect values from a real Citrix Hypervisor instance

    Example usage:
    $ export TEST_CITRIX_USER='XXXXX' TEST_CITRIX_PASS='XXXXX'
    $ TEST_CITRIX_RUN_LAB=true ddev test citrix_hypervisor:py38 -k test_lab

    """
    if not is_affirmative(os.environ.get('TEST_CITRIX_RUN_LAB')):
        pytest.skip(
            "Skipped! Set TEST_CITRIX_RUN_LAB to run this test. "
            "TEST_CITRIX_USER and TEST_CITRIX_PASS must also be set."
        )

    username = os.environ['TEST_CITRIX_USER']
    password = os.environ['TEST_CITRIX_PASS']

    instances = [
        {
            'url': 'http://aws.citrixhost/b',
            'username': username,
            'password': password,
        },
        {
            'url': 'http://aws.citrixhost/c',
            'username': username,
            'password': password,
        },
        {
            'url': 'http://aws.citrixhost/d',
            'username': username,
            'password': password,
        },
    ]

    for instance in instances:
        check = CitrixHypervisorCheck('citrix_hypervisor', {}, [instance])
        check._check_connection()
        dd_run_check(check)

        aggregator.assert_service_check('citrix_hypervisor.can_connect', CitrixHypervisorCheck.OK)
        for m in METRICS:
            aggregator.assert_metric('citrix_hypervisor.{}'.format(m), at_least=0)

        aggregator.assert_all_metrics_covered()
        aggregator.assert_metrics_using_metadata(get_metadata_metrics())
        aggregator.reset()
