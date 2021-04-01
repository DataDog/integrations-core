# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

import pytest

from datadog_checks.base import is_affirmative
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
    $ TEST_VSPHERE_RUN_LAB=true ddev test vsphere:py38 -k test_lab

    """
    if not is_affirmative(os.environ.get('TEST_VSPHERE_RUN_LAB')):
        pytest.skip(
            "Skipped! Set TEST_VSPHERE_RUN_LAB to run this test. "
            "TEST_VSPHERE_USER and TEST_VSPHERE_PASS must also be set."
        )
    username = os.environ['TEST_VSPHERE_USER']
    password = os.environ['TEST_VSPHERE_PASS']
    instance = {
        'host': 'aws.vcenter.localdomain',
        'username': username,
        'password': password,
        'collection_level': 4,
        'collection_type': 'both',
        'use_legacy_check_version': False,
        'collect_metric_instance_values': True,
        'ssl_verify': False,
        'collect_tags': True,
        'collect_attributes': True,
        'rest_api_options': {
            'timeout': '5',
        },
    }
    check = VSphereCheck('vsphere', {}, [instance])
    check.initiate_api_connection()
    check.check(instance)

    # Basic assert
    aggregator.assert_metric('vsphere.cpu.coreUtilization.avg')
    aggregator.assert_metric_has_tag('vsphere.cpu.usage.avg', 'MyCategoryFoo:MyTagFoo')  # verify collect_tags works
    print("TOTAL metrics: {}".format(len(aggregator._metrics)))

    # Write all metrics to a file
    f = open(os.path.join(HERE, 'metrics_lab.csv'), 'w')
    f.write("name,host,type,value,tags\n")
    for metrics in aggregator._metrics.values():
        for m in metrics:
            f.write("{},{},{},{},\"{}\"\n".format(m.name, m.hostname, m.type, m.value, m.tags))
