# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import win32serviceutil

from datadog_checks.base.checks.windows.perf_counters.base import PerfCountersBaseCheckWithLegacySupport

from .metrics import METRICS_CONFIG

SERVICE_METRIC_MAP = {
    'Netlogon': ['Netlogon', 'Security System-Wide Statistics'],
    'DHCPServer': ['DHCP Server'],
    'DFSR': ['DFS Replicated Folders'],
}


def _service_exists(service_name):
    try:
        win32serviceutil.QueryServiceStatus(service_name)
    except Exception:
        return False
    return True


def _get_existing_services():
    return {service for service in SERVICE_METRIC_MAP.keys() if _service_exists(service)}


class ActiveDirectoryCheckV2(PerfCountersBaseCheckWithLegacySupport):
    __NAMESPACE__ = 'active_directory'

    def get_default_config(self):
        """Build metrics configuration based on service availability."""
        filtered_metrics_config = {
            'NTDS': METRICS_CONFIG['NTDS'],  # Include NTDS metrics by default
        }
        existing_services = _get_existing_services()

        for service in existing_services:
            for service_metric_name in SERVICE_METRIC_MAP[service]:
                filtered_metrics_config[service_metric_name] = METRICS_CONFIG[service_metric_name]

        return {'metrics': filtered_metrics_config}
