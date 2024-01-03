# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import ctypes
import re

import pywintypes
import win32service
import winerror
from six import raise_from

from datadog_checks.base import AgentCheck

SERVICE_PATTERN_FLAGS = re.IGNORECASE

SERVICE_CONFIG_TRIGGER_INFO = 8


def QueryServiceConfig2W(*args):
    """
    ctypes wrapper for info types not supported by pywin32
    """
    if ctypes.windll.advapi32.QueryServiceConfig2W(*args) == 0:
        raise ctypes.WinError()


class TriggerInfo(ctypes.Structure):
    _fields_ = [("triggerCount", ctypes.c_uint32), ("pTriggers", ctypes.c_void_p), ("pReserved", ctypes.c_char_p)]


class ServiceFilter(object):
    def __init__(self, name=None, startup_type=None, trigger_start=None):
        self.name = name
        self.startup_type = startup_type
        self.trigger_start = trigger_start

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
        if self.trigger_start is not None:
            if not self.trigger_start and service_view.trigger_count > 0:
                return False
            elif self.trigger_start and service_view.trigger_count == 0:
                return False
        return True

    def __str__(self):
        vals = []
        if self.name is not None:
            vals.append('name={}'.format(self._name_re.pattern))
        if self.startup_type is not None:
            vals.append('startup_type={}'.format(self.startup_type))
        if self.trigger_start is not None:
            vals.append('trigger_start={}'.format(self.trigger_start))
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
            trigger_start = item.get('trigger_start', None)
            obj = cls(name=name, startup_type=startup_type, trigger_start=trigger_start)
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
        self._trigger_count = None

    def __str__(self):
        vals = []
        if self.name is not None:
            vals.append('name={}'.format(self.name))
        if self._startup_type is not None:
            vals.append('startup_type={}'.format(self.startup_type_string()))
        if self._trigger_count is not None:
            vals.append('trigger_count={}'.format(self._trigger_count))
        # Example:
        #   - Service(name=EventLog)
        #   - Service(name=Dnscache, startup_type=automatic, trigger_count=1)
        return '{}({})'.format("Service", ', '.join(vals))

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

    @property
    def trigger_count(self):
        if self._trigger_count is None:
            # find out how many bytes to allocate for buffer
            # raise error if the error code is not ERROR_INSUFFICIENT_BUFFER
            bytesneeded = ctypes.c_uint32(0)
            try:
                QueryServiceConfig2W(
                    ctypes.c_void_p(self.hSvc.handle), SERVICE_CONFIG_TRIGGER_INFO, None, 0, ctypes.byref(bytesneeded)
                )
            except OSError as e:
                if e.winerror != winerror.ERROR_INSUFFICIENT_BUFFER:
                    raise

            # allocate buffer and get trigger info
            # raise any error from QueryServiceConfig2W
            bytesBuffer = ctypes.create_string_buffer(bytesneeded.value)
            QueryServiceConfig2W(
                ctypes.c_void_p(self.hSvc.handle),
                SERVICE_CONFIG_TRIGGER_INFO,
                ctypes.byref(bytesBuffer),
                bytesneeded,
                ctypes.byref(bytesneeded),
            )

            # converting returned buffer into TriggerInfo to get trigger count
            triggerStruct = TriggerInfo.from_buffer(bytesBuffer)
            self._trigger_count = triggerStruct.triggerCount

        return self._trigger_count

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

        # Sort service filters in reverse order on the regex pattern so more specific (longer)
        # regex patterns are tested first. This is to handle cases when a pattern is a prefix of
        # another pattern.
        # Service filters without a name field don't report UNKNOWN, but if they match a service
        # before a filter with a name then the name filter may report UNKONWN. Reverse sorting on
        # the length prevents this by putting service filters without a name last in the list.
        # See test_name_regex_order()
        service_filters = sorted(service_filters, reverse=True, key=lambda x: len(x.name or ""))

        for short_name, _, service_status in service_statuses:
            service_view = ServiceView(scm_handle, short_name)

            if 'ALL' not in services:
                for service_filter in service_filters:
                    try:
                        if service_filter.match(service_view):
                            self.log.debug('Matched %s with %s', service_view, service_filter)
                            services_unseen.discard(service_filter.name)
                            break
                        else:
                            self.log.debug('Did not match %s with %s', service_view, service_filter)
                    except (pywintypes.error, OSError) as e:
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
