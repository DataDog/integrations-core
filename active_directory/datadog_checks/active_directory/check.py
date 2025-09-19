# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import win32service
import win32serviceutil

from datadog_checks.base.checks.windows.perf_counters.base import PerfCountersBaseCheckWithLegacySupport

from .metrics import METRICS_CONFIG

SERVICE_METRIC_MAP = {
    'NTDS': ['NTDS'],
    'Netlogon': ['Netlogon', 'Security System-Wide Statistics'],
    'DHCPServer': ['DHCP Server'],
    'DFSR': ['DFS Replicated Folders'],
}


class ActiveDirectoryCheckV2(PerfCountersBaseCheckWithLegacySupport):
    __NAMESPACE__ = 'active_directory'

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        # Remove configure_perf_objects from initialization since we need to call it
        # every time the check runs to adapt to changing service states
        if self.configure_perf_objects in self.check_initializations:
            self.check_initializations.remove(self.configure_perf_objects)

    def _get_windows_service_state(self, service_name):
        try:
            status = win32serviceutil.QueryServiceStatus(service_name)
        except Exception as e:
            self.log.debug('Unable to query service status: %s', e)
            return None
        return status.dwCurrentState

    def _get_running_services(self):
        return {
            service
            for service in SERVICE_METRIC_MAP.keys()
            if self._get_windows_service_state(service) == win32service.SERVICE_RUNNING
        }

    def get_default_config(self):
        """Build metrics configuration based on service availability."""
        filtered_metrics_config = {}
        running_services = self._get_running_services()

        for service in running_services:
            for metric in SERVICE_METRIC_MAP[service]:
                filtered_metrics_config[metric] = METRICS_CONFIG[metric]

        return {'metrics': filtered_metrics_config}

    def check(self, _):
        self.configure_perf_objects()
        super().check(_)
