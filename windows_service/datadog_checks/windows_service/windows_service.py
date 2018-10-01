# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import win32service
from six import iteritems

from datadog_checks.checks import AgentCheck


class WindowsService(AgentCheck):
    SERVICE_CHECK_NAME = 'windows_service.state'
    # https://docs.microsoft.com/en-us/windows/desktop/api/winsvc/ns-winsvc-_service_status
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

    def check(self, instance):
        services = set(instance.get('services', []))
        custom_tags = instance.get('tags', [])

        if not services:
            raise ValueError('No services defined in configuration.')

        # Old-style WMI wildcards
        if 'host' in instance:
            services = set(service.replace('%', '.*') for service in services)

        service_patterns = {service: re.compile(service) for service in services}
        services_unseen = set(services)

        try:
            scm_handle = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ENUMERATE_SERVICE)
        except Exception as e:  # no cov
            raise Exception('Unable to open SCManager: {}'.format(e))

        type_filter = win32service.SERVICE_WIN32
        state_filter = win32service.SERVICE_STATE_ALL

        service_statuses = win32service.EnumServicesStatus(scm_handle, type_filter, state_filter)

        for short_name, desc, service_status in service_statuses:
            if 'ALL' not in services:
                for service, service_pattern in iteritems(service_patterns):
                    if service_pattern.match(short_name):
                        services_unseen.discard(service)
                        break
                else:
                    continue

            state = service_status[1]
            status = self.STATE_TO_STATUS.get(state, self.UNKNOWN)

            tags = ['service:{}'.format(short_name)]
            tags.extend(custom_tags)

            self.service_check(self.SERVICE_CHECK_NAME, status, tags=tags)
            self.log.debug('service state for {} {}'.format(short_name, status))

        if 'ALL' not in services:
            for service in services_unseen:
                status = self.CRITICAL

                tags = ['service:{}'.format(service)]
                tags.extend(custom_tags)

                self.service_check(self.SERVICE_CHECK_NAME, status, tags=tags)
                self.log.debug('service state for {} {}'.format(service, status))
