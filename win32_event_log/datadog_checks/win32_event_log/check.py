# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import pywintypes
import win32con
import win32event
import win32evtlog
import win32security
from six import PY2

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.base.errors import SkipInstanceError
from datadog_checks.base.utils.common import exclude_undefined_keys
from datadog_checks.base.utils.time import get_timestamp

from .filters import construct_xpath_query
from .legacy import Win32EventLogWMI

if PY2:
    ConfigMixin = object
else:
    from .config_models import ConfigMixin


class Win32EventLogCheck(AgentCheck, ConfigMixin):
    # The lower cased version of the `API SOURCE ATTRIBUTE` column from the table located here:
    # https://docs.datadoghq.com/integrations/faq/list-of-api-source-attribute-value/
    SOURCE_TYPE_NAME = 'event viewer'

    # NOTE: Keep this in sync with config spec:
    # instances.start.value.enum
    #
    # https://docs.microsoft.com/en-us/windows/win32/api/winevt/ne-winevt-evt_subscribe_flags
    START_OPTIONS = {
        'now': win32evtlog.EvtSubscribeToFutureEvents,
        'oldest': win32evtlog.EvtSubscribeStartAtOldestRecord,
    }

    # NOTE: Keep this in sync with config spec:
    # instances.auth_type.value.enum
    #
    # https://docs.microsoft.com/en-us/windows/win32/api/winevt/ne-winevt-evt_rpc_login_flags
    LOGIN_FLAGS = {
        'default': win32evtlog.EvtRpcLoginAuthDefault,
        'negotiate': win32evtlog.EvtRpcLoginAuthNegotiate,
        'kerberos': win32evtlog.EvtRpcLoginAuthKerberos,
        'ntlm': win32evtlog.EvtRpcLoginAuthNTLM,
    }

    LEGACY_PARAMS = (
        'host',
        'log_file',
        'source_name',
        'type',
        'event_id',
        'message_filters',
        'event_format',
    )

    # https://docs.microsoft.com/en-us/windows/win32/wes/eventmanifestschema-leveltype-complextype#remarks
    #
    # From
    # https://docs.microsoft.com/en-us/windows/win32/wes/eventmanifestschema-eventdefinitiontype-complextype#attributes:
    #
    # > If you do not specify a level, the event descriptor will contain a zero for level.
    LEVEL_TO_ALERT_TYPE = {0: 'info', 1: 'error', 2: 'error', 3: 'warning', 4: 'info', 5: 'info'}

    def __new__(cls, name, init_config, instances):
        instance = instances[0]

        init_config_legacy_mode = init_config.get('legacy_mode', None)
        init_config_legacy_mode_v2 = init_config.get('legacy_mode_v2', None)
        # If legacy_mode is unset for an instance, default to the init_config option
        use_legacy_mode = instance.get('legacy_mode', init_config_legacy_mode)
        use_legacy_mode_v2 = instance.get('legacy_mode_v2', init_config_legacy_mode_v2)

        # If legacy_mode and legacy_mode_v2 are unset, default to legacy mode for configuration backwards compatibility
        if use_legacy_mode is None and not is_affirmative(use_legacy_mode_v2):
            use_legacy_mode = True

        use_legacy_mode = is_affirmative(use_legacy_mode)
        use_legacy_mode_v2 = is_affirmative(use_legacy_mode_v2)

        if use_legacy_mode and use_legacy_mode_v2:
            raise ConfigurationError(
                "legacy_mode and legacy_mode_v2 are both true. Each instance must set a single mode to true."
            )

        if use_legacy_mode:
            # Supports PY2 and PY3
            return Win32EventLogWMI(name, init_config, instances)
        elif use_legacy_mode_v2:
            # Supports PY3
            if PY2:
                raise ConfigurationError("legacy_mode_v2 is not supported on Python2")
            return super(Win32EventLogCheck, cls).__new__(cls)
        else:
            raise SkipInstanceError(
                "Set the legacy_mode and legacy_mode_v2 options to configure the implementation to use."
            )

    def __init__(self, name, init_config, instances):
        super(Win32EventLogCheck, self).__init__(name, init_config, instances)

        # Raw user-defined query or one we construct based on filters
        self._query = None

        # Create a pull subscription and its signaler on the first check run
        self._subscription = None
        self._event_handle = None

        # Cache a handle to the System event deserialization request
        self._render_context_system = None

        # Cache a handle to the EventData/UserData event deserialization request
        self._render_context_data = None

        # Create a bookmark handle which will be updated on saves to disk
        self._bookmark_handle = None

        # Session used for remote connections, or None if local connection
        self._session = None

        # Whether or not to interpret messages for unknown sources
        self._interpret_messages = is_affirmative(
            self.instance.get('interpret_messages', self.init_config.get('interpret_messages', True))
        )

        # These will become compiled regular expressions if any relevant patterns are defined in the config
        self._included_messages = None
        self._excluded_messages = None

        self._event_priority = self.instance.get('event_priority', self.init_config.get('event_priority', 'normal'))

        self.check_initializations.append(self.parse_config)
        self.check_initializations.append(self.construct_query)
        self.check_initializations.append(self.create_session)
        self.check_initializations.append(self.init_subscription)

        # Define every property collector
        self._collectors = [self.collect_timestamp, self.collect_fqdn, self.collect_level, self.collect_provider]

        if is_affirmative(self.instance.get('tag_event_id', self.init_config.get('tag_event_id', False))):
            self._collectors.append(self.collect_event_id)

        if is_affirmative(self.instance.get('tag_sid', self.init_config.get('tag_sid', False))):
            self._collectors.append(self.collect_sid)

        for legacy_param in self.LEGACY_PARAMS:
            if legacy_param in self.instance:
                self.log.warning(
                    "%s config option is ignored unless running legacy mode. Please remove it", legacy_param
                )

    def check(self, _):
        for event in self.consume_events():
            try:
                rendered_event = self.render_event(event, self._render_context_system)
            except Exception as e:
                self.log.error('Unable to render event: %s', e)
                continue

            # Build up the event payload
            event_payload = {
                'source_type_name': self.SOURCE_TYPE_NAME,
                'priority': self._event_priority,
                'tags': list(self.config.tags) if self.config.tags is not None else [],
            }

            # As seen in every collector, before using members of the enum you need to check for existence. See:
            # https://docs.microsoft.com/en-us/windows/win32/api/winevt/ne-winevt-evt_system_property_id
            # https://docs.microsoft.com/en-us/windows/win32/api/winevt/ns-winevt-evt_variant
            for collector in self._collectors:
                # Any collector may indicate that events need to be filtered out by returning False
                if collector(event_payload, rendered_event, event) is False:
                    break
            else:
                self.event(event_payload)

    def collect_timestamp(self, event_payload, rendered_event, event_object):
        value, variant = rendered_event[win32evtlog.EvtSystemTimeCreated]
        if variant == win32evtlog.EvtVarTypeNull:
            event_payload['timestamp'] = get_timestamp()
            return

        event_payload['timestamp'] = get_timestamp(value)

    def collect_fqdn(self, event_payload, rendered_event, event_object):
        value, variant = rendered_event[win32evtlog.EvtSystemComputer]
        if variant == win32evtlog.EvtVarTypeNull or self._session is None:
            event_payload['host'] = self.hostname
            return

        event_payload['host'] = value

    def collect_level(self, event_payload, rendered_event, event_object):
        value, variant = rendered_event[win32evtlog.EvtSystemLevel]
        if variant == win32evtlog.EvtVarTypeNull:
            return

        event_payload['alert_type'] = self.LEVEL_TO_ALERT_TYPE.get(value, 'error')

    def collect_provider(self, event_payload, rendered_event, event_object):
        value, variant = rendered_event[win32evtlog.EvtSystemProviderName]
        if variant == win32evtlog.EvtVarTypeNull:
            return

        event_payload['aggregation_key'] = value
        event_payload['msg_title'] = '{}/{}'.format(self.config.path, value)

        message = None

        # See https://docs.microsoft.com/en-us/windows/win32/wes/getting-a-provider-s-metadata-
        try:
            # https://docs.microsoft.com/en-us/windows/win32/api/winevt/nf-winevt-evtopenpublishermetadata
            metadata = win32evtlog.EvtOpenPublisherMetadata(value)
        # Code 2: The system cannot find the file specified.
        except pywintypes.error as e:
            if self._interpret_messages:
                message = self.interpret_message(event_object)
            else:
                self.log_windows_error(e)
        else:  # no cov
            try:
                # https://docs.microsoft.com/en-us/windows/win32/api/winevt/nf-winevt-evtformatmessage
                # https://docs.microsoft.com/en-us/windows/win32/api/winevt/ne-winevt-evt_format_message_flags
                message = win32evtlog.EvtFormatMessage(metadata, event_object, win32evtlog.EvtFormatMessageEvent)
            # Code 15027: The message resource is present but the message was not found in the message table.
            # Code 15028: The message ID for the desired message could not be found.
            except pywintypes.error as e:
                if self._interpret_messages:
                    message = self.interpret_message(event_object)
                else:
                    self.log_windows_error(e)

        if message is not None:
            message = self.sanitize_message(message.rstrip())

            if self.message_filtered(message):
                return False

            event_payload['msg_text'] = message

    def collect_event_id(self, event_payload, rendered_event, event_object):
        # https://docs.microsoft.com/en-us/windows/win32/eventlog/event-identifiers
        value, variant = rendered_event[win32evtlog.EvtSystemEventID]
        if variant == win32evtlog.EvtVarTypeNull:
            return

        # Beware of documentation
        #
        # According to https://docs.microsoft.com/en-us/windows/win32/wes/eventschema-systempropertiestype-complextype
        #
        # > A legacy provider uses a 32-bit number to identify its events. If the event is logged by
        #   a legacy provider, the value of EventID element contains the low-order 16 bits of the event
        #   identifier and the Qualifier attribute contains the high-order 16 bits of the event identifier.
        #
        # The implication is that the real value is something like: (qualifier << 16) | event_id
        #
        # However, that is referring to an entirely different struct which we do not use:
        # https://docs.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-eventlogrecord
        event_payload['tags'].append('event_id:{}'.format(value))

    def collect_sid(self, event_payload, rendered_event, event_object):
        value, variant = rendered_event[win32evtlog.EvtSystemUserID]
        if variant == win32evtlog.EvtVarTypeNull:
            return

        try:
            # https://docs.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-lookupaccountsida
            # https://mhammond.github.io/pywin32/win32security__LookupAccountSid_meth.html
            user, domain, _ = win32security.LookupAccountSid(
                None if self._session is None else event_payload['host'], value
            )
        except win32security.error as e:
            self.log_windows_error(e)
        else:
            event_payload['tags'].append('sid:{}\\{}'.format(domain, user))

    def render_event(self, event, context):
        # See https://docs.microsoft.com/en-us/windows/win32/wes/rendering-events

        # https://docs.microsoft.com/en-us/windows/win32/api/winevt/nf-winevt-evtrender
        # https://docs.microsoft.com/en-us/windows/win32/api/winevt/ne-winevt-evt_render_flags
        # https://mhammond.github.io/pywin32/win32evtlog__EvtRender_meth.html
        return win32evtlog.EvtRender(event, win32evtlog.EvtRenderEventValues, Context=context)

    def consume_events(self):
        # Define out here and let loop shadow so we can update the bookmark one final time at the end of the check run
        event = None

        events_since_last_bookmark = 0
        for event in self.poll_events():
            events_since_last_bookmark += 1

            if events_since_last_bookmark >= self.config.bookmark_frequency:
                events_since_last_bookmark = 0
                self.update_bookmark(event)

            yield event

        if events_since_last_bookmark:
            self.update_bookmark(event)

    def poll_events(self):
        while True:
            # IMPORTANT: the subscription starts immediately so you must consume before waiting for the first signal
            while True:
                # https://docs.microsoft.com/en-us/windows/win32/api/winevt/nf-winevt-evtnext
                # https://mhammond.github.io/pywin32/win32evtlog__EvtNext_meth.html
                #
                # Behavior when you call the EvtNext and there are no events to read (i.e. polling).
                # Python 2: An error saying EvtNext: The operation identifier is not valid happens.
                #           This is logged as a debug line.
                # Python 3: Returns an empty tuple
                try:
                    events = win32evtlog.EvtNext(self._subscription, self.config.payload_size)
                except pywintypes.error as e:
                    self.log_windows_error(e)
                    if (
                        e.winerror == 15007  # ERROR_EVT_CHANNEL_NOT_FOUND: The specified channel could not be found.
                        or e.winerror == 6  # ERROR_INVALID_HANDLE_VALUE: The handle is invalid
                    ):
                        # Can happen if the event publisher is unregistered,
                        # which sometimes happens during software updates.
                        # Must get a new subscription handle.
                        self.reset_subscription()
                    break
                else:
                    if not events:
                        break

                for event in events:
                    yield event

            # https://docs.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitforsingleobjectex
            # https://mhammond.github.io/pywin32/win32event__WaitForSingleObjectEx_meth.html
            wait_signal = win32event.WaitForSingleObjectEx(self._event_handle, self.config.timeout, True)

            # No more events, end check run
            if wait_signal != win32con.WAIT_OBJECT_0:
                break

    def update_bookmark(self, event):
        # See https://docs.microsoft.com/en-us/windows/win32/wes/bookmarking-events

        # https://docs.microsoft.com/en-us/windows/win32/api/winevt/nf-winevt-evtupdatebookmark
        # https://mhammond.github.io/pywin32/win32evtlog__EvtUpdateBookmark_meth.html
        win32evtlog.EvtUpdateBookmark(self._bookmark_handle, event)

        # https://docs.microsoft.com/en-us/windows/win32/api/winevt/nf-winevt-evtrender
        # https://mhammond.github.io/pywin32/win32evtlog__EvtRender_meth.html
        bookmark_xml = win32evtlog.EvtRender(self._bookmark_handle, win32evtlog.EvtRenderBookmark)

        self.write_persistent_cache('bookmark', bookmark_xml)

    def parse_config(self):
        for option in ('included_messages', 'excluded_messages'):
            if option not in self.instance:
                continue

            pattern, error = self._compile_patterns(self.instance[option])
            if error is not None:
                raise ConfigurationError('Error compiling pattern for option `{}`: {}'.format(option, error))

            setattr(self, '_{}'.format(option), pattern)

        password = self.config.password
        if password:
            self.register_secret(password)

    def construct_query(self):
        query = self.config.query
        if query:
            self._query = query
            return

        self._query = construct_xpath_query(exclude_undefined_keys(self.config.filters.dict()))
        self.log.debug('Using constructed query: %s', self._query)

    def create_session(self):
        session_struct = self.get_session_struct()

        # No need for a remote connection
        if session_struct is None:
            return

        # https://docs.microsoft.com/en-us/windows/win32/api/winevt/nf-winevt-evtopensession
        # https://mhammond.github.io/pywin32/win32evtlog__EvtOpenSession_meth.html
        self._session = win32evtlog.EvtOpenSession(session_struct, win32evtlog.EvtRpcLogin, 0, 0)

    def init_subscription(self):
        # https://docs.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-createeventa
        # https://mhammond.github.io/pywin32/win32event__CreateEvent_meth.html
        self._event_handle = win32event.CreateEvent(None, 0, 0, self.check_id)

        bookmark = self.read_persistent_cache('bookmark')
        if bookmark:
            flags = win32evtlog.EvtSubscribeStartAfterBookmark
        else:
            flags = self.START_OPTIONS[self.config.start]

            # Set explicitly to None rather than a potentially empty string
            bookmark = None

        # https://docs.microsoft.com/en-us/windows/win32/api/winevt/nf-winevt-evtcreatebookmark
        # https://mhammond.github.io/pywin32/win32evtlog__EvtCreateBookmark_meth.html
        self._bookmark_handle = win32evtlog.EvtCreateBookmark(bookmark)

        self.create_subscription(flags, bookmark)

        # https://docs.microsoft.com/en-us/windows/win32/api/winevt/nf-winevt-evtcreaterendercontext
        # https://docs.microsoft.com/en-us/windows/win32/api/winevt/ne-winevt-evt_render_context_flags
        self._render_context_system = win32evtlog.EvtCreateRenderContext(win32evtlog.EvtRenderContextSystem)
        self._render_context_data = win32evtlog.EvtCreateRenderContext(win32evtlog.EvtRenderContextUser)

    def create_subscription(self, flags, bookmark):
        # https://docs.microsoft.com/en-us/windows/win32/api/winevt/nf-winevt-evtsubscribe
        # https://mhammond.github.io/pywin32/win32evtlog__EvtSubscribe_meth.html
        self._subscription = win32evtlog.EvtSubscribe(
            self.config.path,
            flags,
            SignalEvent=self._event_handle,
            Query=self._query,
            Session=self._session,
            Bookmark=self._bookmark_handle if bookmark else None,
        )

    def reset_subscription(self):
        # Destroy old subscription
        # Important so that it doesn't affect event or bookmark handle states.
        self._subscription = None
        # Create new subscription
        self.create_subscription(win32evtlog.EvtSubscribeStartAfterBookmark, True)

    def get_session_struct(self):
        server = self.instance.get('server', 'localhost')
        if server in ('localhost', '127.0.0.1'):
            return

        auth_type = self.instance.get('auth_type', 'default')
        if auth_type not in self.LOGIN_FLAGS:
            raise ConfigurationError('Invalid `auth_type`, must be one of: {}'.format(', '.join(self.LOGIN_FLAGS)))

        user = self.instance.get('user', self.instance.get('username'))
        domain = self.instance.get('domain')
        password = self.instance.get('password')

        # https://docs.microsoft.com/en-us/windows/win32/api/winevt/ns-winevt-evt_rpc_login
        # https://mhammond.github.io/pywin32/PyEVT_RPC_LOGIN.html
        return server, user, domain, password, self.LOGIN_FLAGS[auth_type]

    def log_windows_error(self, exc):
        # https://mhammond.github.io/pywin32/error.html
        #
        # Occasionally the Windows function returns some extra data after a colon which we don't need
        self.log.debug('Error code %d when calling `%s`: %s', exc.winerror, exc.funcname.split(':')[0], exc.strerror)

    def message_filtered(self, message):
        return self._message_excluded(message) or not self._message_included(message)

    def _message_included(self, message):
        if self._included_messages is None:
            return True

        return not not self._included_messages.search(message)

    def _message_excluded(self, message):
        if self._excluded_messages is None:
            return False

        return not not self._excluded_messages.search(message)

    @staticmethod
    def _compile_patterns(patterns):
        valid_patterns = []

        for pattern in patterns:
            # Ignore empty patterns as they match everything
            if not pattern:
                continue

            try:
                re.compile(pattern)
            except Exception as e:
                return None, str(e)
            else:
                valid_patterns.append(pattern)

        return re.compile('|'.join(valid_patterns)), None

    def interpret_message(self, event_object):
        rendered_event = self.render_event(event_object, self._render_context_data)

        lines = []
        for value, variant in rendered_event:
            if variant != win32evtlog.EvtVarTypeString:
                break

            lines.append(value)

        if lines:
            return '\n'.join(lines)

    @staticmethod
    def sanitize_message(message):
        # https://github.com/mhammond/pywin32/pull/1524#issuecomment-633152961
        return message.replace('\u200e', '')

    @staticmethod
    def render_event_xml(event):  # no cov
        """
        Helper function used only for debugging purposes.
        """
        return win32evtlog.EvtRender(event, win32evtlog.EvtRenderEventXml)
