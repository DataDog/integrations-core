# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.iis.iis import DEFAULT_COUNTERS
from datadog_checks.iis.metrics import METRICS_CONFIG
from datadog_checks.iis.service_check import IIS_APPLICATION_POOL_STATE

CHECK_NAME = 'iis'
MINIMAL_INSTANCE = {'host': '.'}

INSTANCE = {
    'host': '.',
    'sites': ['Default Web Site', 'Exchange Back End', 'Non Existing Website'],
    'app_pools': ['DefaultAppPool', 'MSExchangeServicesAppPool', 'Non Existing App Pool'],
}

INVALID_HOST_INSTANCE = {'host': 'nonexistinghost'}

WIN_SERVICES_LEGACY_CONFIG = {'host': '.', 'use_legacy_check_version': True}

WIN_SERVICES_MINIMAL_CONFIG = {'host': '.', 'tags': ['mytag1', 'mytag2']}

WIN_SERVICES_CONFIG = {
    'host': '.',
    'tags': ['mytag1', 'mytag2'],
    'sites': ['Default Web Site', 'Exchange Back End', 'Failing site'],
    'app_pools': ['DefaultAppPool', 'MSExchangeServicesAppPool', 'Failing app pool'],
}

DEFAULT_SITES = ['Default_Web_Site', 'Exchange_Back_End', 'Total']
DEFAULT_APP_POOLS = [
    '.NET_v4.5',
    '.NET_v4.5_Classic',
    'DefaultAppPool',
    'MSExchangeAutodiscoverAppPool',
    'MSExchangeECPAppPool',
    'MSExchangeOABAppPool',
    'MSExchangeOWAAppPool',
    'MSExchangeOWACalendarAppPool',
    'MSExchangePowerShellAppPool',
    'MSExchangePowerShellFrontEndAppPool',
    'MSExchangeRpcProxyAppPool',
    'MSExchangeServicesAppPool',
    'MSExchangeSyncAppPool',
    'Total',
]

SITE_METRICS = [counter_data[3] for counter_data in DEFAULT_COUNTERS if counter_data[0] == 'Web Service']
APP_POOL_METRICS = [counter_data[3] for counter_data in DEFAULT_COUNTERS if counter_data[0] == 'APP_POOL_WAS']

PERFORMANCE_OBJECTS = {}
# Set arbitrary values for the counters
for object_name, instances in (('APP_POOL_WAS', ['foo-pool', 'bar-pool']), ('Web Service', ['foo.site', 'bar.site'])):
    PERFORMANCE_OBJECTS[object_name] = (
        instances,
        {counter: [9000, 0] for counter in METRICS_CONFIG[object_name]['counters'][0]},
    )
# Set a specific value for the app pool service check counter
# \APP_POOL_WAS(<INSTANCE>)\Current Application Pool State
PERFORMANCE_OBJECTS['APP_POOL_WAS'][1]['Current Application Pool State'] = [IIS_APPLICATION_POOL_STATE['Running'], 0]
