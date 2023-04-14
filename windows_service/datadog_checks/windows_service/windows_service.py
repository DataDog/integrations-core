# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import pywintypes
import win32service
from six import raise_from

from datadog_checks.base import AgentCheck

SERVICE_PATTERN_FLAGS = re.IGNORECASE


class ServiceFilter(object):
    def __init__(self, name=None, startup_type=None):
        self.name = name
        self.startup_type = startup_type

        self._init_patterns()

    def _init_patterns(self):
        try:
            if self.name is not None:
                pattern = self.name
                self._name_re = re.compile(pattern, SERVICE_PATTERN_FLAGS)
        except re.error as e:
            raise_from(Exception("Regular expression syntax error in '{}': {}".format(pattern, str(e))), None)

    def match(self, service_view):
        if self.name is not None:
            if not self._name_re.match(service_view.name):
                return False
        if self.startup_type is not None:
            if self.startup_type.lower() != service_view.startup_type_string().lower():
                return False
        return True

    def __str__(self):
        vals = []
        if self.name is not None:
            vals.append('name={}'.format(self._name_re.pattern))
        if self.startup_type is not None:
            vals.append('startup_type={}'.format(self.startup_type))
        # Example:
        #   - ServiceFilter(name=EventLog)
        #   - ServiceFilter(startup_type=automatic)
        return '{}({})'.format(type(self).__name__, ', '.join(vals))

    @classmethod
    def _wmi_compat_name(cls, name):
        # Old-style WMI wildcards
        return name.replace('%', '.*')

    @classmethod
    def from_config(cls, item, wmi_compat=False):
        if isinstance(item, str):
            # Example config
            '''
            services:
              - service_name
            '''
            name = item
            if wmi_compat:
                name = cls._wmi_compat_name(name)
            obj = cls(name=name)
        elif isinstance(item, dict):
            # Example config
            '''
            services:
              - name: service_name
              - startup_type: automatic
            '''
            name = item.get('name', None)
            if name is not None and wmi_compat:
                name = cls._wmi_compat_name(name)
            startup_type = item.get('startup_type', None)
            obj = cls(name=name, startup_type=startup_type)
        else:
            raise Exception("Invalid type '{}' for service".format(type(item).__name__))
        return obj


class ServiceView(object):
    # map service startup types to strings for ServiceFilter and windows_service_startup_type tag values
    STARTUP_TYPE_TO_STRING = {
        win32service.SERVICE_AUTO_START: "automatic",
        win32service.SERVICE_DEMAND_START: "manual",
        win32service.SERVICE_DISABLED: "disabled",
    }
    STARTUP_TYPE_DELAYED_AUTO = "automatic_delayed_start"
    STARTUP_TYPE_UNKNOWN = "unknown"

    def __init__(self, scm_handle, name):
        self.scm_handle = scm_handle
        self.name = name

        self._hSvc = None
        self._startup_type = None
        self._service_config = None
        self._is_delayed_auto = None

    @property
    def hSvc(self):
        if self._hSvc is None:
            self._hSvc = win32service.OpenService(self.scm_handle, self.name, win32service.SERVICE_QUERY_CONFIG)
        return self._hSvc

    @property
    def service_config(self):
        if self._service_config is None:
            self._service_config = win32service.QueryServiceConfig(self.hSvc)
        return self._service_config

    @property
    def startup_type(self):
        if self._startup_type is None:
            self._startup_type = self.service_config[1]
        return self._startup_type

    @property
    def is_delayed_auto(self):
        if self._is_delayed_auto is None:
            self._is_delayed_auto = win32service.QueryServiceConfig2(
                self.hSvc, win32service.SERVICE_CONFIG_DELAYED_AUTO_START_INFO
            )
        return self._is_delayed_auto

    def startup_type_string(self):
        startup_type_string = ''
        startup_type_string = self.STARTUP_TYPE_TO_STRING.get(self.startup_type, self.STARTUP_TYPE_UNKNOWN)
        if self.startup_type == win32service.SERVICE_AUTO_START and self.is_delayed_auto:
            startup_type_string = self.STARTUP_TYPE_DELAYED_AUTO
        return startup_type_string


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

    def check(self, instance):
        services = instance.get('services', [])
        custom_tags = instance.get('tags', [])

        if not services:
            raise ValueError('No services defined in configuration.')

        # Old-style WMI wildcards
        if 'host' in instance:
            wmi_compat = True
        else:
            wmi_compat = False

        service_filters = [ServiceFilter.from_config(item, wmi_compat=wmi_compat) for item in services]
        services_unseen = {f.name for f in service_filters if f.name is not None}

        try:
            scm_handle = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ENUMERATE_SERVICE)
        except Exception as e:  # no cov
            raise Exception('Unable to open SCManager: {}'.format(e))

        type_filter = win32service.SERVICE_WIN32
        state_filter = win32service.SERVICE_STATE_ALL

        service_statuses = win32service.EnumServicesStatus(scm_handle, type_filter, state_filter)

        for short_name, _, service_status in service_statuses:
            service_view = ServiceView(scm_handle, short_name)

            if 'ALL' not in services:
                for service_filter in service_filters:
                    self.log.debug('Service Short Name: %s and Filter: %s', short_name, service_filter)
                    try:
                        if service_filter.match(service_view):
                            services_unseen.discard(service_filter.name)
                            break
                    except pywintypes.error as e:
                        self.log.exception("Exception at service match for %s", service_filter)
                        self.warning(
                            "Failed to query %s service config for filter %s: %s", short_name, service_filter, str(e)
                        )
                else:
                    continue

            state = service_status[1]
            status = self.STATE_TO_STATUS.get(state, self.UNKNOWN)

            tags = ['windows_service:{}'.format(short_name)]
            tags.extend(custom_tags)

            if instance.get('windows_service_startup_type_tag', False):
                try:
                    tags.append('windows_service_startup_type:{}'.format(service_view.startup_type_string()))
                except pywintypes.error as e:
                    self.log.exception("Exception at windows_service_startup_type tag for %s", service_filter)
                    self.warning(
                        "Failed to query %s service config for filter %s: %s", short_name, service_filter, str(e)
                    )

            if not instance.get('disable_legacy_service_tag', False):
                self._log_deprecation('service_tag', 'windows_service')
                tags.append('service:{}'.format(short_name))

            self.service_check(self.SERVICE_CHECK_NAME, status, tags=tags)
            self.log.debug('service state for %s %s', short_name, status)

        if 'ALL' not in services:
            for service in services_unseen:
                # if a name doesn't match anything (wrong name or no permission to access the service), report UNKNOWN
                status = self.UNKNOWN
                startup_type_string = ServiceView.STARTUP_TYPE_UNKNOWN

                tags = ['windows_service:{}'.format(service)]

                tags.extend(custom_tags)

                if instance.get('windows_service_startup_type_tag', False):
                    tags.append('windows_service_startup_type:{}'.format(startup_type_string))

                if not instance.get('disable_legacy_service_tag', False):
                    self._log_deprecation('service_tag', 'windows_service')
                    tags.append('service:{}'.format(service))

                self.service_check(self.SERVICE_CHECK_NAME, status, tags=tags)
                self.log.debug('service state for %s %s', service, status)
