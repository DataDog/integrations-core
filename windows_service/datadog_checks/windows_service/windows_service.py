# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import win32service
from six import iteritems

from datadog_checks.base import AgentCheck

SERVICE_PATTERN_FLAGS = re.IGNORECASE


class WindowsService(AgentCheck):
    SERVICE_CHECK_NAME = 'windows_service.state'
    # https://docs.microsoft.com/en-us/windows/win32/api/winsvc/ns-winsvc-service_status_process
    STATE_TO_STATUS = {
        # STOPPED
        1: AgentCheck.CRITICAL,
        # START_PENDING
        2: AgentCheck.WARNING,
        # STOP_PENDING
        3: AgentCheck.WARNING,
        # RUNNING
        4: AgentCheck.OK,
        # CONTINUE_PENDING
        5: AgentCheck.WARNING,
        # PAUSE_PENDING
        6: AgentCheck.WARNING,
        # PAUSED
        7: AgentCheck.WARNING,
    }
    # windows_service_startup_type tag values
    STARTUP_TYPE_TO_STRING = {
        win32service.SERVICE_AUTO_START: "automatic",
        win32service.SERVICE_DEMAND_START: "manual",
        win32service.SERVICE_DISABLED: "disabled",
    }
    STARTUP_TYPE_DELAYED_AUTO = "automatic_delayed_start"
    STARTUP_TYPE_UNKNOWN = "unknown"

    def check(self, instance):
        services = set(instance.get('services', []))
        custom_tags = instance.get('tags', [])

        if not services:
            raise ValueError('No services defined in configuration.')

        # Old-style WMI wildcards
        if 'host' in instance:
            services = set(service.replace('%', '.*') for service in services)

        service_patterns = {service: re.compile(service, SERVICE_PATTERN_FLAGS) for service in services}
        services_unseen = set(services)

        try:
            scm_handle = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ENUMERATE_SERVICE)
        except Exception as e:  # no cov
            raise Exception('Unable to open SCManager: {}'.format(e))

        type_filter = win32service.SERVICE_WIN32
        state_filter = win32service.SERVICE_STATE_ALL

        service_statuses = win32service.EnumServicesStatus(scm_handle, type_filter, state_filter)

        for short_name, _, service_status in service_statuses:
            if 'ALL' not in services:
                for service, service_pattern in sorted(iteritems(service_patterns), reverse=True):
                    self.log.debug(
                        'Service: %s with Short Name: %s and Pattern: %s', service, short_name, service_pattern.pattern
                    )
                    if service_pattern.match(short_name):
                        services_unseen.discard(service)
                        break
                else:
                    continue

            state = service_status[1]
            status = self.STATE_TO_STATUS.get(state, self.UNKNOWN)

            tags = ['windows_service:{}'.format(short_name)]
            tags.extend(custom_tags)

            if instance.get('windows_service_startup_type_tag', False):
                startup_type_string = self._get_service_startup_type_tag(scm_handle, short_name)
                tags.append('windows_service_startup_type:{}'.format(startup_type_string))

            if not instance.get('disable_legacy_service_tag', False):
                self._log_deprecation('service_tag', 'windows_service')
                tags.append('service:{}'.format(short_name))

            self.service_check(self.SERVICE_CHECK_NAME, status, tags=tags)
            self.log.debug('service state for %s %s', short_name, status)

        if 'ALL' not in services:
            for service in services_unseen:
                # if a name doesn't match anything (wrong name or no permission to access the service), report UNKNOWN
                status = self.UNKNOWN
                startup_type_string = self.STARTUP_TYPE_UNKNOWN

                tags = ['windows_service:{}'.format(service)]

                tags.extend(custom_tags)

                if instance.get('windows_service_startup_type_tag', False):
                    tags.append('windows_service_startup_type:{}'.format(startup_type_string))

                if not instance.get('disable_legacy_service_tag', False):
                    self._log_deprecation('service_tag', 'windows_service')
                    tags.append('service:{}'.format(service))

                self.service_check(self.SERVICE_CHECK_NAME, status, tags=tags)
                self.log.debug('service state for %s %s', service, status)

    def _get_service_startup_type(self, scm_handle, service_name):
        """
        Returns a tuple that describes the startup type for the service
          - QUERY_SERVICE_CONFIG.dwStartType
          - SERVICE_CONFIG_DELAYED_AUTO_START_INFO.fDelayedAutostart
        """
        hSvc = win32service.OpenService(scm_handle, service_name, win32service.SERVICE_QUERY_CONFIG)
        service_config = win32service.QueryServiceConfig(hSvc)
        startup_type = service_config[1]
        if startup_type == win32service.SERVICE_AUTO_START:
            # Query if auto start is delayed
            is_delayed_auto = win32service.QueryServiceConfig2(
                hSvc, win32service.SERVICE_CONFIG_DELAYED_AUTO_START_INFO
            )
        else:
            is_delayed_auto = False
        return startup_type, is_delayed_auto

    def _get_service_startup_type_tag(self, scm_handle, service_name):
        try:
            startup_type, is_delayed_auto = self._get_service_startup_type(scm_handle, service_name)
            startup_type_string = self.STARTUP_TYPE_TO_STRING.get(startup_type, self.STARTUP_TYPE_UNKNOWN)
            if startup_type == win32service.SERVICE_AUTO_START and is_delayed_auto:
                startup_type_string = self.STARTUP_TYPE_DELAYED_AUTO
        except Exception as e:
            self.warning("Failed to query service config for %s: %s", service_name, str(e))
            startup_type_string = self.STARTUP_TYPE_UNKNOWN

        return startup_type_string
