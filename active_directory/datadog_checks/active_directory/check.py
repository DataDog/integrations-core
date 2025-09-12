# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import win32service
import win32serviceutil
from datadog_checks.base.checks.windows.perf_counters.base import PerfCountersBaseCheckWithLegacySupport

from .metrics import METRICS_CONFIG

SERVICE_METRIC_MAP = {
    'NTDS': {'NTDS'},
    'Netlogon': {'Netlogon', 'Security System-Wide Statistics'},
    'DHCPServer': {'DHCP Server'},
    'DFSR': {'DFS Replicated Folders'},
}


def _get_windows_service_state(service_name):
    status = win32serviceutil.QueryServiceStatus(service_name)
    return status.dwCurrentState


def _get_running_services():
    return {
        service
        for service in SERVICE_METRIC_MAP.keys()
        if _get_windows_service_state(service) == win32service.SERVICE_RUNNING
    }


class ActiveDirectoryCheckV2(PerfCountersBaseCheckWithLegacySupport):
    __NAMESPACE__ = 'active_directory'

    def get_default_config(self):
        """Build metrics configuration based on service availability."""

        running_services = _get_running_services()
        metrics_to_collect = set()
        for service in running_services:
            metrics_to_collect.update(SERVICE_METRIC_MAP[service])

        filtered_metrics_config = {metric: METRICS_CONFIG[metric] for metric in metrics_to_collect}

        return {'metrics': filtered_metrics_config}
