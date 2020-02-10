# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

import pytest

from datadog_checks.vsphere import VSphereCheck

from .common import HERE


def test_lab(aggregator):
    """
    This test is intended to be run manually to connect to a real vSphere Instance

    It's useful for:
    - QA/testing the integration with a real vSphere instance
    - using a debugger to inspect values from a real vSphere instance
    - analysing the metrics received, see `metrics_lab.csv` below

    Example usage:
    $ export TEST_VSPHERE_USER='XXXXX' TEST_VSPHERE_PASS='XXXXX'
    $ ddev test vsphere:py37 -k test_lab

    """
    username = os.environ.get('TEST_VSPHERE_USER')
    password = os.environ.get('TEST_VSPHERE_PASS')
    if not username or not password:
        pytest.skip("Skipped! TEST_VSPHERE_USER and TEST_VSPHERE_PASS are needed to run this test")
    instance = {
        'host': 'aws.vcenter.localdomain',
        'username': username,
        'password': password,
        'collection_level': 4,
        'collection_type': 'both',
        'use_legacy_check_version': False,
        'collect_metric_instance_values': True,
        'ssl_verify': False,
    }
    check = VSphereCheck('vsphere', {}, [instance])
    check.initiate_api_connection()
    check.check(instance)

    # Basic assert
    aggregator.assert_metric('vsphere.cpu.coreUtilization.avg')
    print("TOTAL metrics: {}".format(len(aggregator._metrics)))

    # Write all metrics to a file
    f = open(os.path.join(HERE, 'metrics_lab.csv'), 'w')
    f.write("name,host,type,value,tags\n")
    for metrics in aggregator._metrics.values():
        for m in metrics:
            f.write("{},{},{},{},\"{}\"\n".format(m.name, m.hostname, m.type, m.value, m.tags))
