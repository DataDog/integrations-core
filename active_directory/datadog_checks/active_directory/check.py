# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
# datadog_checks/active_directory/check.py

import platform
import time

from datadog_checks.base.checks.windows.perf_counters.base import PerfCountersBaseCheckWithLegacySupport


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

    # Services that should always have their metrics collected
    REQUIRED_METRICS = ['NTDS']  # Core AD metrics

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)

        # Get instance configuration
        instance = instances[0] if instances else {}

        # Configuration options
        self.service_check_enabled = instance.get('service_check_enabled', True)
        self.force_all_metrics = instance.get('force_all_metrics', False)

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
        # On non-Windows platforms, always return True
        if not self._is_windows:
            if not self._platform_warning_logged:
                self.log.info("Running on non-Windows platform, assuming all services are available")
                self._platform_warning_logged = True
            return True

        try:
            # Import Windows-specific modules
            import win32service  # type: ignore
            import win32serviceutil  # type: ignore

            # Query service status with timeout
            status = win32serviceutil.QueryServiceStatus(service_name)

            # status[1] is the current state
            # SERVICE_RUNNING = 4
            is_running = status[1] == win32service.SERVICE_RUNNING

            return is_running

        except ImportError as e:
            self.log.error("pywin32 not available: %s", e)
            self.log.info("Install pywin32 to enable service detection")
            return True  # Assume available if we can't check

        except Exception as e:
            # Re-raise as this is an actual error
            raise Exception("Service check failed for {}: {}".format(service_name, str(e)))

    def _build_config_from_cache(self, metrics_config):
        import json

        """Build configuration using cached service states."""
        filtered_config = {'metrics': {}}

        # Always include required metrics
        for metric_name in self.REQUIRED_METRICS:
            if metric_name in metrics_config:
                filtered_config['metrics'][metric_name] = metrics_config[metric_name]
                self.log.debug("Including required metric: %s", metric_name)

        # Add metrics based on service availability
        metrics_added = set(self.REQUIRED_METRICS)

        for service, metric_names in self.SERVICE_METRIC_MAP.items():
            service_running = self._service_cache.get(service, True)  # Default to True

            if service_running:
                for metric_name in metric_names:
                    if metric_name in metrics_config and metric_name not in metrics_added:
                        filtered_config['metrics'][metric_name] = metrics_config[metric_name]
                        metrics_added.add(metric_name)
                        self.log.error("Including %s (service %s is running)", metric_name, service)
            else:
                self.log.error("Excluding metrics %s (service %s not running)", metric_names, service)

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

        self.log.error(json.dumps(filtered_config, indent=4))
        return filtered_config

    def check(self, _):
        """
        Perform the check.

        The perf-counter layer keeps its compiled counter list between runs,
        so we have to *pro-actively* refresh the service cache and invalidate
        that compiled list whenever the cache is considered expired.
        """
        if self.service_check_enabled and not self.force_all_metrics:
            now = time.time()
            if now - self._last_service_check >= self._cache_duration:
                self.log.debug("Service cache expired after %.1fs - refreshing", now - self._last_service_check)
                self._refresh_service_cache()
                self._last_service_check = now

                # Make sure PerfCountersBaseCheckWithLegacySupport recompiles
                # its counter set using the *new* service cache.
                if hasattr(self, "_config"):
                    self._config = None

        return super().check(_)
