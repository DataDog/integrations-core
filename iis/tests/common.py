# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.iis.iis import DEFAULT_COUNTERS

CHECK_NAME = 'iis'
MINIMAL_INSTANCE = {'host': '.'}

INSTANCE = {
    'host': '.',
    'sites': ['Default Web Site', 'Exchange Back End', 'Non Existing Website'],
    'app_pools': ['DefaultAppPool', 'MSExchangeServicesAppPool', 'Non Existing App Pool'],
}

INVALID_HOST_INSTANCE = {'host': 'nonexistinghost'}

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
