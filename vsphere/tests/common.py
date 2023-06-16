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

legacy_default_instance = {
    'name': 'vsphere_mock',
    'empty_default_hostname': True,
    'event_config': {
        'collect_vcenter_alarms': True,
    },
    'use_legacy_check_version': True,
    'host': 'vsphere_host',
    'username': 'vsphere_username',
    'password': 'vsphere_password',
}

legacy_realtime_instance = {
    'name': 'vsphere_mock',
    'empty_default_hostname': True,
    'event_config': {
        'collect_vcenter_alarms': True,
    },
    'use_legacy_check_version': True,
    'host': 'vsphere_host',
    'username': 'vsphere_username',
    'password': 'vsphere_password',
    'collect_realtime_only': True,
}

legacy_historical_instance = {
    'name': 'vsphere_mock',
    'empty_default_hostname': True,
    'event_config': {
        'collect_vcenter_alarms': True,
    },
    'use_legacy_check_version': True,
    'host': 'vsphere_host',
    'username': 'vsphere_username',
    'password': 'vsphere_password',
    'collect_historical_only': True,
}

default_instance = {
    'empty_default_hostname': True,
    'use_legacy_check_version': False,
    'host': 'vsphere_host',
    'username': 'vsphere_username',
    'password': 'vsphere_password',
}

realtime_instance = {
    'collection_level': 4,
    'empty_default_hostname': True,
    'use_legacy_check_version': False,
    'host': 'vsphere_host',
    'username': 'vsphere_username',
    'password': 'vsphere_password',
    'ssl_verify': False,
    'rest_api_options': None,
}

historical_instance = {
    'collection_level': 1,
    'empty_default_hostname': True,
    'use_legacy_check_version': False,
    'host': 'vsphere_host',
    'username': 'vsphere_username',
    'password': 'vsphere_password',
    'ssl_verify': False,
    'collection_type': 'historical',
}


def build_rest_api_client(config, logger):
    if VSPHERE_VERSION.startswith('7.'):
        return VSphereRestAPI(config, logger, False)
    return VSphereRestAPI(config, logger, True)
