# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.constants import ServiceCheck

# Maps "\APP_POOL_WAS(<INSTANCE>)\Current Application Pool State" values
# Values found in Performance Monitor
# TODO: Use a python Enum when we drop Python 2 support
IIS_APPLICATION_POOL_STATE = {
    'Uninitialized': 1,
    'Initialized': 2,
    'Running': 3,
    'Disabling': 4,
    'Disabled': 5,
    'Shutdown Pending': 6,
    'Delete Pending': 7
}
# Add int -> string mapping to the dict
IIS_APPLICATION_POOL_STATE.update({v: k for k, v in IIS_APPLICATION_POOL_STATE.items()})


def site_service_check(uptime):
    # For sites the "\Web Service(<INSTANCE>)\Service Uptime" counter resets
    # to 0 when the site is stopped. So we can use it for the service check.
    uptime = int(uptime)
    if uptime == 0:
        return ServiceCheck.CRITICAL
    return ServiceCheck.OK


def app_pool_service_check(status):
    # For app pools we can't use "\APP_POOL_WAS(<INSTANCE>)\Current Application Pool Uptime" for
    # the service check because it does NOT reset to 0 when the app pool is stopped. It only
    # resets to 0 once the app pool is started again.
    # Instead we use the "\APP_POOL_WAS(<INSTANCE>)\Current Application Pool State" counter which
    # reports whether the app pool is running, stopping, etc.
    status = int(status)
    if status == IIS_APPLICATION_POOL_STATE['Running']:
        return ServiceCheck.OK
    return ServiceCheck.CRITICAL
