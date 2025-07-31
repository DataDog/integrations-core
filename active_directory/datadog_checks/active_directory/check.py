# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
# datadog_checks/active_directory/check.py

import platform
import time

from datadog_checks.base.checks.windows.perf_counters.base import PerfCountersBaseCheckWithLegacySupport
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.base.utils.windows_service import STATE_TO_STATUS, is_service_running


class ActiveDirectoryCheckV2(PerfCountersBaseCheckWithLegacySupport):
    __NAMESPACE__ = 'active_directory'

    # Service to Performance Object mapping
    SERVICE_METRIC_MAP = {
        'NTDS': ['NTDS'],  # Core AD service - always collect these metrics
        'Netlogon': ['Netlogon', 'Security System-Wide Statistics'],
        'DHCPServer': ['DHCP Server'],
        'DFSR': ['DFS Replicated Folders'],
        'DNS': [],  # Service monitoring only for now
        'W32Time': [],  # Service monitoring only for now
        'ADWS': [],  # Service monitoring only for now
        'Kdc': [],  # Service monitoring only for now
    }

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)

        # Get instance configuration
        instance = instances[0] if instances else {}

        # Configuration options
        self.service_check_enabled = instance.get('service_check_enabled', True)
        self.force_all_metrics = instance.get('force_all_metrics', False)
        self.emit_service_status = instance.get('emit_service_status', False)
        self.service_check_timeout = instance.get('service_check_timeout', 5)

        # Caching configuration
        self._service_cache = {}
        self._cache_duration = instance.get('service_cache_duration', 300)  # 5 minutes
        self._last_service_check = 0

        # Platform detection
        self._is_windows = platform.system() == 'Windows'

        # Track if we've logged platform warnings
        self._platform_warning_logged = False

    def get_default_config(self):
        """Build metrics configuration based on service availability."""
        from .metrics import METRICS_CONFIG

        # Short circuit if forced collection
        if self.force_all_metrics:
            self.log.debug("Force collecting all metrics (force_all_metrics=true)")
            return {'metrics': METRICS_CONFIG}

        # Short circuit if service checking disabled
        if not self.service_check_enabled:
            self.log.debug("Service checking disabled, collecting all metrics")
            return {'metrics': METRICS_CONFIG}

        # Use cached results if recent
        current_time = time.time()
        if current_time - self._last_service_check < self._cache_duration:
            self.log.debug("Using cached service states (age: %.1fs)", current_time - self._last_service_check)
            return self._build_config_from_cache(METRICS_CONFIG)

        # Refresh cache
        self.log.debug("Refreshing service state cache")
        self._refresh_service_cache()
        self._last_service_check = current_time

        return self._build_config_from_cache(METRICS_CONFIG)

    def _refresh_service_cache(self):
        """Refresh service availability cache."""
        # Clear old cache
        self._service_cache.clear()

        # Get all services we need to check
        services_to_check = set()
        for service in self.SERVICE_METRIC_MAP.keys():
            services_to_check.add(service)

        # Check each service
        for service in services_to_check:
            # NTDS is always considered running (core AD service)
            if service == 'NTDS':
                self._service_cache[service] = True
                self.log.debug("Service NTDS: always collected (core AD service)")
                continue

            try:
                is_running = self._is_service_running(service)
                self._service_cache[service] = is_running
                self.log.debug("Service %s: %s", service, 'running' if is_running else 'not running')
            except Exception as e:
                self.log.warning("Failed to check service %s: %s", service, e)
                # Optimistically assume service is available on error
                self._service_cache[service] = True

    def _is_service_running(self, service_name):
        """Check if a Windows service is running."""
        # Use shared utility function
        is_running, state, error = is_service_running(service_name, self.log)

        if error:
            # Log error but optimistically assume service is available
            self.log.warning("Failed to check service %s: %s", service_name, error)
            return True

        return is_running

    def _build_config_from_cache(self, metrics_config):
        """Build configuration using cached service states."""
        filtered_config = {'metrics': {}}
        metrics_added = set()

        # Add metrics based on service availability
        for service, metric_names in self.SERVICE_METRIC_MAP.items():
            service_running = self._service_cache.get(service, True)  # Default to True

            if service_running:
                for metric_name in metric_names:
                    if metric_name in metrics_config and metric_name not in metrics_added:
                        filtered_config['metrics'][metric_name] = metrics_config[metric_name]
                        metrics_added.add(metric_name)
                        self.log.debug("Including %s (service %s is running)", metric_name, service)
            else:
                self.log.info("Excluding metrics %s (service %s not running)", metric_names, service)

        # Add any metrics not controlled by services
        # This ensures backward compatibility if new metrics are added
        for metric_name, metric_config in metrics_config.items():
            if metric_name not in metrics_added:
                # Check if this metric is controlled by any service
                controlled = False
                for service_metrics in self.SERVICE_METRIC_MAP.values():
                    if metric_name in service_metrics:
                        controlled = True
                        break

                if not controlled:
                    filtered_config['metrics'][metric_name] = metric_config
                    self.log.debug("Including uncontrolled metric: %s", metric_name)

        return filtered_config

    def check(self, _):
        """Perform the check and emit service status if configured."""
        # Emit service checks if enabled
        if self.emit_service_status and self.service_check_enabled:
            self._emit_service_checks()

        # Call parent check
        return super().check(_)

    def _emit_service_checks(self):
        """Emit service status as Datadog service checks."""
        # Only emit on Windows
        if not self._is_windows:
            return

        # Define AD services to monitor
        AD_SERVICES = {
            'NTDS': 'NT Directory Services',
            'DNS': 'DNS Service',
            'Kdc': 'Key Distribution Center',
            'Netlogon': 'Net Logon',
            'W32Time': 'Windows Time Service',
            'DFSR': 'Distributed File System Replication',
            'ADWS': 'Active Directory Web Services',
        }

        # Check each service efficiently using direct lookups
        for service_name, description in AD_SERVICES.items():
            check_name = "{}.service.{}".format(self.__NAMESPACE__, service_name.lower())

            # Use shared utility to get service state
            is_running, state, error = is_service_running(service_name, self.log)

            if error:
                if "not found" in error.lower():
                    # Service doesn't exist on this system
                    self.service_check(
                        check_name, ServiceCheck.UNKNOWN, message="{} not found".format(description), tags=[]
                    )
                else:
                    # Other error (permissions, etc.)
                    self.service_check(
                        check_name,
                        ServiceCheck.UNKNOWN,
                        message="Failed to check {}: {}".format(description, error),
                        tags=[],
                    )
            else:
                # Map state to service check status
                status = STATE_TO_STATUS.get(state, ServiceCheck.UNKNOWN)

                if status == ServiceCheck.OK:
                    message = "{} is running".format(description)
                else:
                    message = "{} is not running (state: {})".format(description, state)

                self.service_check(check_name, status, message=message, tags=[])
