# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
# datadog_checks/active_directory/check.py

import platform
import threading
import time

from datadog_checks.base.checks.windows.perf_counters.base import PerfCountersBaseCheckWithLegacySupport
from datadog_checks.base.utils.windows import get_windows_service_states


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

        # Thread safety
        self._lock = threading.Lock()

        # Caching configuration
        self._service_cache = {}
        self._config_cache = None  # Cache the built configuration

        # Validate and set cache duration
        cache_duration = instance.get('service_cache_duration', 300)
        try:
            cache_duration = float(cache_duration)
            # Enforce reasonable bounds: 60 seconds to 1 hour
            if cache_duration < 60:
                self.log.warning("service_cache_duration too low (%s), using minimum of 60 seconds", cache_duration)
                cache_duration = 60
            elif cache_duration > 3600:
                self.log.warning("service_cache_duration too high (%s), using maximum of 3600 seconds", cache_duration)
                cache_duration = 3600
        except (TypeError, ValueError):
            self.log.warning("Invalid service_cache_duration value, using default of 300 seconds")
            cache_duration = 300

        self._cache_duration = cache_duration
        self._last_service_check = 0

        # Platform detection
        self._is_windows = platform.system() == 'Windows'

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
        with self._lock:
            current_time = time.time()
            if current_time - self._last_service_check < self._cache_duration:
                self.log.debug("Using cached service states (age: %.1fs)", current_time - self._last_service_check)
                # Return cached config if available
                if self._config_cache is not None:
                    return self._config_cache
                # Otherwise build and cache it
                self._config_cache = self._build_config_from_cache(METRICS_CONFIG)
                return self._config_cache

        # Refresh cache
        with self._lock:
            # Double-check after acquiring lock (another thread might have refreshed)
            current_time = time.time()
            if current_time - self._last_service_check < self._cache_duration:
                if self._config_cache is not None:
                    return self._config_cache

            self.log.debug("Refreshing service state cache")
            self._refresh_service_cache()
            self._last_service_check = current_time

            # Build and cache the new config
            self._config_cache = self._build_config_from_cache(METRICS_CONFIG)
            return self._config_cache

    def _refresh_service_cache(self):
        """Refresh service availability cache."""
        # Clear old cache
        self._service_cache.clear()

        # Get all services we need to check
        services_to_check = set(self.SERVICE_METRIC_MAP.keys())

        try:
            # Get service states using shared utility
            service_states = get_windows_service_states(services_to_check, self.log)

            # Process each service
            for service, state in service_states.items():
                if state is None:
                    # Service not found on system
                    self._service_cache[service] = False
                    self.log.debug("Service %s not found on system", service)
                elif state == 4:  # SERVICE_RUNNING
                    self._service_cache[service] = True
                    self.log.debug("Service %s is running", service)
                else:
                    self._service_cache[service] = False
                    self.log.debug("Service %s is not running (state: %d)", service, state)

        except ImportError:
            # pywin32 not available on Windows - this is a real problem
            self.log.error("Cannot check services: pywin32 not installed")
            # Set all to False - we can't verify they're running
            for service in services_to_check:
                self._service_cache[service] = False

        except Exception as e:
            # Enumeration failed - could be permissions or other issue
            self.log.error("Failed to enumerate services: %s", e)
            # Set all to False - we can't verify they're running
            for service in services_to_check:
                self._service_cache[service] = False

    def _is_service_running(self, service_name):
        """Check if a Windows service is running."""
        try:
            states = get_windows_service_states({service_name}, self.log)
            state = states.get(service_name)

            if state is None:
                self.log.debug("Service %s not found", service_name)
                return False

            return state == 4  # SERVICE_RUNNING

        except Exception as e:
            self.log.error("Failed to check service %s: %s", service_name, e)
            return False  # Conservative - assume not running if can't check

    def _build_config_from_cache(self, metrics_config):
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
                        self.log.debug("Including %s (service %s is running)", metric_name, service)
            else:
                self.log.debug("Excluding metrics %s (service %s not running)", metric_names, service)

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
        """
        Perform the check.

        The perf-counter layer keeps its compiled counter list between runs,
        so we have to *pro-actively* refresh the service cache and invalidate
        that compiled list whenever the cache is considered expired.
        """
        if self.service_check_enabled and not self.force_all_metrics:
            with self._lock:
                now = time.time()
                if now - self._last_service_check >= self._cache_duration:
                    self.log.debug("Service cache expired after %.1fs - refreshing", now - self._last_service_check)
                    self._refresh_service_cache()
                    self._last_service_check = now

                    # Clear cached config
                    self._config_cache = None

                    # Make sure PerfCountersBaseCheckWithLegacySupport recompiles
                    # its counter set using the *new* service cache.
                    if hasattr(self, "_config"):
                        self._config = None

        return super().check(_)
