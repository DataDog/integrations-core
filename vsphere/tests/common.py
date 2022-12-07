# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

from datadog_checks.vsphere.api_rest import VSphereRestAPI

HERE = os.path.abspath(os.path.dirname(__file__))

VSPHERE_VERSION = os.environ.get('VSPHERE_VERSION')

LAB_USERNAME = os.environ.get('TEST_VSPHERE_USER')
LAB_PASSWORD = os.environ.get('TEST_VSPHERE_PASS')

LAB_INSTANCE = {
    'host': 'aws.vcenter.localdomain',
    'username': LAB_USERNAME,
    'password': LAB_PASSWORD,
    'collection_level': 4,
    'collection_type': 'both',
    'use_legacy_check_version': False,
    'collect_metric_instance_values': True,
    'empty_default_hostname': True,
    'ssl_verify': False,
    'collect_tags': True,
    'collect_events': True,
    'use_collect_events_fallback': True,
}


def build_rest_api_client(config, logger):
    if VSPHERE_VERSION.startswith('7.'):
        return VSphereRestAPI(config, logger, False)
    return VSphereRestAPI(config, logger, True)
