# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import inspect
import json
import logging
import re
import traceback
import unicodedata
from collections import defaultdict
from os.path import basename

import yaml
from six import PY3, iteritems, text_type

from ..config import is_affirmative
from ..constants import ServiceCheck
from ..utils.agent.debug import enter_pdb
from ..utils.common import ensure_bytes, ensure_unicode
from ..utils.http import RequestsWrapper
from ..utils.limiter import Limiter
from ..utils.proxy import config_proxy_skip

try:
    import datadog_agent
    from ..log import init_logging

    init_logging()
except ImportError:
    from ..stubs import datadog_agent
    from ..stubs.log import init_logging

    init_logging()

try:
    import aggregator

    using_stub_aggregator = False
except ImportError:
    from ..stubs import aggregator

    using_stub_aggregator = True


if datadog_agent.get_config('disable_unsafe_yaml'):
    from ..ddyaml import monkey_patch_pyyaml

    monkey_patch_pyyaml()


# Metric types for which it's only useful to submit once per set of tags
ONE_PER_CONTEXT_METRIC_TYPES = [aggregator.GAUGE, aggregator.RATE, aggregator.MONOTONIC_COUNT]


class __AgentCheckPy3(object):
    """
    The base class for any Agent based integrations
    """

    # If defined, this will be the prefix of every metric/service check and the source type of events
    __NAMESPACE__ = ''

    OK, WARNING, CRITICAL, UNKNOWN = ServiceCheck

    # Used by `self.http` RequestsWrapper
    HTTP_CONFIG_REMAPPER = None

    """
    DEFAULT_METRIC_LIMIT allows to set a limit on the number of metric name and tags combination
    this check can send per run. This is useful for checks that have an unbounded
    number of tag values that depend on the input payload.
    The logic counts one set of tags per gauge/rate/monotonic_count call, and deduplicates
    sets of tags for other metric types. The first N sets of tags in submission order will
    be sent to the aggregator, the rest are dropped. The state is reset after each run.

    See https://github.com/DataDog/integrations-core/pull/2093 for more information
    """
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, *args, **kwargs):
        """
        args: `name`, `init_config`, `agentConfig` (deprecated), `instances`
        """
        self.metrics = defaultdict(list)
        self.check_id = ''
        self.instances = kwargs.get('instances', [])
        self.name = kwargs.get('name', '')
        self.init_config = kwargs.get('init_config', {})
        self.agentConfig = kwargs.get('agentConfig', {})
        self.warnings = []
        self.metric_limiter = None

        if len(args) > 0:
            self.name = args[0]
        if len(args) > 1:
            self.init_config = args[1]
        if len(args) > 2:
            if len(args) > 3 or 'instances' in kwargs:
                # old-style init: the 3rd argument is `agentConfig`
                self.agentConfig = args[2]
                if len(args) > 3:
                    self.instances = args[3]
            else:
                # new-style init: the 3rd argument is `instances`
                self.instances = args[2]

        # Agent 6+ will only have one instance
        self.instance = self.instances[0] if self.instances else None

        # `self.hostname` is deprecated, use `datadog_agent.get_hostname()` instead
        self.hostname = datadog_agent.get_hostname()

        # the agent5 'AgentCheck' setup a log attribute.
        self.log = logging.getLogger('{}.{}'.format(__name__, self.name))

        # Provides logic to yield consistent network behavior based on user configuration.
        # Only new checks or checks on Agent 6.13+ can and should use this for HTTP requests.
        self._http = None

        # TODO: Remove with Agent 5
        # Set proxy settings
        self.proxies = self._get_requests_proxy()
        if not self.init_config:
            self._use_agent_proxy = True
        else:
            self._use_agent_proxy = is_affirmative(self.init_config.get('use_agent_proxy', True))

        # TODO: Remove with Agent 5
        self.default_integration_http_timeout = float(self.agentConfig.get('default_integration_http_timeout', 9))

        self._deprecations = {
            'increment': [
                False,
                (
                    'DEPRECATION NOTICE: `AgentCheck.increment`/`AgentCheck.decrement` are deprecated, please '
                    'use `AgentCheck.gauge` or `AgentCheck.count` instead, with a different metric name'
                ),
            ],
            'device_name': [
                False,
                (
                    'DEPRECATION NOTICE: `device_name` is deprecated, please use a `device:` '
                    'tag in the `tags` list instead'
                ),
            ],
            'in_developer_mode': [
                False,
                'DEPRECATION NOTICE: `in_developer_mode` is deprecated, please stop using it.',
            ],
            'no_proxy': [
                False,
                (
                    'DEPRECATION NOTICE: The `no_proxy` config option has been renamed '
                    'to `skip_proxy` and will be removed in Agent version 6.13.'
                ),
            ],
        }

        # Setup metric limits
        try:
            metric_limit = self.instances[0].get('max_returned_metrics', self.DEFAULT_METRIC_LIMIT)
            # Do not allow to disable limiting if the class has set a non-zero default value
            if metric_limit == 0 and self.DEFAULT_METRIC_LIMIT > 0:
                metric_limit = self.DEFAULT_METRIC_LIMIT
                self.warning(
                    'Setting max_returned_metrics to zero is not allowed, reverting '
                    'to the default of {} metrics'.format(self.DEFAULT_METRIC_LIMIT)
                )
        except Exception:
            metric_limit = self.DEFAULT_METRIC_LIMIT
        if metric_limit > 0:
            self.metric_limiter = Limiter(self.name, 'metrics', metric_limit, self.warning)

    @staticmethod
    def load_config(yaml_str):
        """
        Convenience wrapper to ease programmatic use of this class from the C API.
        """
        return yaml.safe_load(yaml_str)

    @property
    def http(self):
        if self._http is None:
            self._http = RequestsWrapper(self.instance or {}, self.init_config, self.HTTP_CONFIG_REMAPPER, self.log)

        return self._http

    @property
    def in_developer_mode(self):
        self._log_deprecation('in_developer_mode')
        return False

    def get_instance_proxy(self, instance, uri, proxies=None):
        # TODO: Remove with Agent 5
        proxies = proxies if proxies is not None else self.proxies.copy()

        deprecated_skip = instance.get('no_proxy', None)
        skip = is_affirmative(instance.get('skip_proxy', not self._use_agent_proxy)) or is_affirmative(deprecated_skip)

        if deprecated_skip is not None:
            self._log_deprecation('no_proxy')

        return config_proxy_skip(proxies, uri, skip)

    def _context_uid(self, mtype, name, tags=None, hostname=None):
        return '{}-{}-{}-{}'.format(mtype, name, tags if tags is None else hash(frozenset(tags)), hostname)

    def _format_namespace(self, s):
        if self.__NAMESPACE__:
            return '{}.{}'.format(self.__NAMESPACE__, ensure_unicode(s))

        return ensure_unicode(s)

    def _submit_metric(self, mtype, name, value, tags=None, hostname=None, device_name=None):
        if value is None:
            # ignore metric sample
            return

        tags = self._normalize_tags_type(tags, device_name, name)
        if hostname is None:
            hostname = ''

        if self.metric_limiter:
            if mtype in ONE_PER_CONTEXT_METRIC_TYPES:
                # Fast path for gauges, rates, monotonic counters, assume one set of tags per call
                if self.metric_limiter.is_reached():
                    return
            else:
                # Other metric types have a legit use case for several calls per set of tags, track unique sets of tags
                context = self._context_uid(mtype, name, tags, hostname)
                if self.metric_limiter.is_reached(context):
                    return

        try:
            value = float(value)
        except ValueError:
            err_msg = 'Metric: {} has non float value: {}. Only float values can be submitted as metrics.'.format(
                name, value
            )
            if using_stub_aggregator:
                raise ValueError(err_msg)
            self.warning(err_msg)
            return

        aggregator.submit_metric(self, self.check_id, mtype, self._format_namespace(name), value, tags, hostname)

    def gauge(self, name, value, tags=None, hostname=None, device_name=None):
        self._submit_metric(aggregator.GAUGE, name, value, tags=tags, hostname=hostname, device_name=device_name)

    def count(self, name, value, tags=None, hostname=None, device_name=None):
        self._submit_metric(aggregator.COUNT, name, value, tags=tags, hostname=hostname, device_name=device_name)

    def monotonic_count(self, name, value, tags=None, hostname=None, device_name=None):
        self._submit_metric(
            aggregator.MONOTONIC_COUNT, name, value, tags=tags, hostname=hostname, device_name=device_name
        )

    def rate(self, name, value, tags=None, hostname=None, device_name=None):
        self._submit_metric(aggregator.RATE, name, value, tags=tags, hostname=hostname, device_name=device_name)

    def histogram(self, name, value, tags=None, hostname=None, device_name=None):
        self._submit_metric(aggregator.HISTOGRAM, name, value, tags=tags, hostname=hostname, device_name=device_name)

    def historate(self, name, value, tags=None, hostname=None, device_name=None):
        self._submit_metric(aggregator.HISTORATE, name, value, tags=tags, hostname=hostname, device_name=device_name)

    def increment(self, name, value=1, tags=None, hostname=None, device_name=None):
        self._log_deprecation('increment')
        self._submit_metric(aggregator.COUNTER, name, value, tags=tags, hostname=hostname, device_name=device_name)

    def decrement(self, name, value=-1, tags=None, hostname=None, device_name=None):
        self._log_deprecation('increment')
        self._submit_metric(aggregator.COUNTER, name, value, tags=tags, hostname=hostname, device_name=device_name)

    def _log_deprecation(self, deprecation_key):
        """
        Logs a deprecation notice at most once per AgentCheck instance, for the pre-defined `deprecation_key`
        """
        if not self._deprecations[deprecation_key][0]:
            self.log.warning(self._deprecations[deprecation_key][1])
            self._deprecations[deprecation_key][0] = True

    def service_check(self, name, status, tags=None, hostname=None, message=None):
        tags = self._normalize_tags_type(tags)
        if hostname is None:
            hostname = ''
        if message is None:
            message = ''
        else:
            message = ensure_unicode(message)

        aggregator.submit_service_check(
            self, self.check_id, self._format_namespace(name), status, tags, hostname, message
        )

    def event(self, event):
        # Enforce types of some fields, considerably facilitates handling in go bindings downstream
        for key, value in list(iteritems(event)):
            # transform any bytes objects to utf-8
            if isinstance(value, bytes):
                try:
                    event[key] = event[key].decode('utf-8')
                except UnicodeError:
                    self.log.warning(
                        'Error decoding unicode field `{}` to utf-8 encoded string, cannot submit event'.format(key)
                    )
                    return

        if event.get('tags'):
            event['tags'] = self._normalize_tags_type(event['tags'])
        if event.get('timestamp'):
            event['timestamp'] = int(event['timestamp'])
        if event.get('aggregation_key'):
            event['aggregation_key'] = ensure_unicode(event['aggregation_key'])

        if self.__NAMESPACE__:
            event.setdefault('source_type_name', self.__NAMESPACE__)

        aggregator.submit_event(self, self.check_id, event)

    # TODO(olivier): implement service_metadata if it's worth it
    def service_metadata(self, meta_name, value):
        pass

    def check(self, instance):
        raise NotImplementedError

    def set_external_tags(self, external_tags):
        # Example of external_tags format
        # [
        #     ('hostname', {'src_name': ['test:t1']}),
        #     ('hostname2', {'src2_name': ['test2:t3']})
        # ]
        try:
            for _, source_map in external_tags:
                for src_name, tags in iteritems(source_map):
                    source_map[src_name] = self._normalize_tags_type(tags)
            datadog_agent.set_external_tags(external_tags)
        except IndexError:
            self.log.exception('Unexpected external tags format: {}'.format(external_tags))
            raise

    def normalize(self, metric, prefix=None, fix_case=False):
        """
        Turn a metric into a well-formed metric name
        prefix.b.c
        :param metric The metric name to normalize
        :param prefix A prefix to to add to the normalized name, default None
        :param fix_case A boolean, indicating whether to make sure that the metric name returned is in "snake_case"
        """
        if isinstance(metric, text_type):
            metric = unicodedata.normalize('NFKD', metric).encode('ascii', 'ignore')

        if fix_case:
            name = self.convert_to_underscore_separated(metric)
            if prefix is not None:
                prefix = self.convert_to_underscore_separated(prefix)
        else:
            name = re.sub(br"[,\+\*\-/()\[\]{}\s]", b"_", metric)
        # Eliminate multiple _
        name = re.sub(br"__+", b"_", name)
        # Don't start/end with _
        name = re.sub(br"^_", b"", name)
        name = re.sub(br"_$", b"", name)
        # Drop ._ and _.
        name = re.sub(br"\._", b".", name)
        name = re.sub(br"_\.", b".", name)

        if prefix is not None:
            name = ensure_bytes(prefix) + b"." + name

        return ensure_unicode(name)

    FIRST_CAP_RE = re.compile(br'(.)([A-Z][a-z]+)')
    ALL_CAP_RE = re.compile(br'([a-z0-9])([A-Z])')
    METRIC_REPLACEMENT = re.compile(br'([^a-zA-Z0-9_.]+)|(^[^a-zA-Z]+)')
    DOT_UNDERSCORE_CLEANUP = re.compile(br'_*\._*')

    def convert_to_underscore_separated(self, name):
        """
        Convert from CamelCase to camel_case
        And substitute illegal metric characters
        """
        metric_name = self.FIRST_CAP_RE.sub(br'\1_\2', ensure_bytes(name))
        metric_name = self.ALL_CAP_RE.sub(br'\1_\2', metric_name).lower()
        metric_name = self.METRIC_REPLACEMENT.sub(br'_', metric_name)
        return self.DOT_UNDERSCORE_CLEANUP.sub(br'.', metric_name).strip(b'_')

    def _normalize_tags_type(self, tags, device_name=None, metric_name=None):
        """
        Normalize tags contents and type:
        - append `device_name` as `device:` tag
        - normalize tags type
        - doesn't mutate the passed list, returns a new list
        """
        normalized_tags = []

        if device_name:
            self._log_deprecation('device_name')
            normalized_tags.append('device:{}'.format(ensure_unicode(device_name)))

        if tags is not None:
            for tag in tags:
                if tag is None:
                    continue
                if not isinstance(tag, str):
                    try:
                        tag = tag.decode('utf-8')
                    except Exception:
                        self.log.warning(
                            'Error decoding tag `{}` as utf-8 for metric `{}`, ignoring tag'.format(tag, metric_name)
                        )
                        continue

                normalized_tags.append(tag)

        return normalized_tags

    def warning(self, warning_message):
        warning_message = ensure_unicode(warning_message)

        frame = inspect.currentframe().f_back
        lineno = frame.f_lineno
        # only log the last part of the filename, not the full path
        filename = basename(frame.f_code.co_filename)

        self.log.warning(warning_message, extra={'_lineno': lineno, '_filename': filename})
        self.warnings.append(warning_message)

    def get_warnings(self):
        """
        Return the list of warnings messages to be displayed in the info page
        """
        warnings = self.warnings
        self.warnings = []
        return warnings

    def run(self):
        try:
            instance = copy.deepcopy(self.instances[0])

            if 'set_breakpoint' in self.init_config:
                enter_pdb(self.check, line=self.init_config['set_breakpoint'], args=(instance,))
            else:
                self.check(instance)

            result = ''
        except Exception as e:
            result = json.dumps([{'message': str(e), 'traceback': traceback.format_exc()}])
        finally:
            if self.metric_limiter:
                self.metric_limiter.reset()

        return result

    def _get_requests_proxy(self):
        # TODO: Remove with Agent 5
        no_proxy_settings = {'http': None, 'https': None, 'no': []}

        # First we read the proxy configuration from datadog.conf
        proxies = self.agentConfig.get('proxy', datadog_agent.get_config('proxy'))
        if proxies:
            proxies = proxies.copy()

        # requests compliant dict
        if proxies and 'no_proxy' in proxies:
            proxies['no'] = proxies.pop('no_proxy')

        return proxies if proxies else no_proxy_settings


class __AgentCheckPy2(object):
    """
    The base class for any Agent based integrations
    """

    # If defined, this will be the prefix of every metric/service check and the source type of events
    __NAMESPACE__ = ''

    OK, WARNING, CRITICAL, UNKNOWN = ServiceCheck

    """
    DEFAULT_METRIC_LIMIT allows to set a limit on the number of metric name and tags combination
    this check can send per run. This is useful for checks that have an unbounded
    number of tag values that depend on the input payload.
    The logic counts one set of tags per gauge/rate/monotonic_count call, and deduplicates
    sets of tags for other metric types. The first N sets of tags in submission order will
    be sent to the aggregator, the rest are dropped. The state is reset after each run.

    See https://github.com/DataDog/integrations-core/pull/2093 for more information
    """
    DEFAULT_METRIC_LIMIT = 0

    # Used by `self.http` RequestsWrapper
    HTTP_CONFIG_REMAPPER = None

    def __init__(self, *args, **kwargs):
        """
        args: `name`, `init_config`, `agentConfig` (deprecated), `instances`
        """
        self.metrics = defaultdict(list)
        self.check_id = b''
        self.instances = kwargs.get('instances', [])
        self.name = kwargs.get('name', '')
        self.init_config = kwargs.get('init_config', {})
        self.agentConfig = kwargs.get('agentConfig', {})
        self.warnings = []
        self.metric_limiter = None

        if len(args) > 0:
            self.name = args[0]
        if len(args) > 1:
            self.init_config = args[1]
        if len(args) > 2:
            if len(args) > 3 or 'instances' in kwargs:
                # old-style init: the 3rd argument is `agentConfig`
                self.agentConfig = args[2]
                if len(args) > 3:
                    self.instances = args[3]
            else:
                # new-style init: the 3rd argument is `instances`
                self.instances = args[2]

        # Agent 6+ will only have one instance
        self.instance = self.instances[0] if self.instances else None

        # `self.hostname` is deprecated, use `datadog_agent.get_hostname()` instead
        self.hostname = datadog_agent.get_hostname()

        # the agent5 'AgentCheck' setup a log attribute.
        self.log = logging.getLogger('%s.%s' % (__name__, self.name))

        # Provides logic to yield consistent network behavior based on user configuration.
        # Only new checks or checks on Agent 6.13+ can and should use this for HTTP requests.
        self._http = None

        # TODO: Remove with Agent 5
        # Set proxy settings
        self.proxies = self._get_requests_proxy()
        if not self.init_config:
            self._use_agent_proxy = True
        else:
            self._use_agent_proxy = is_affirmative(self.init_config.get("use_agent_proxy", True))

        self.default_integration_http_timeout = float(self.agentConfig.get('default_integration_http_timeout', 9))

        self._deprecations = {
            'increment': [
                False,
                "DEPRECATION NOTICE: `AgentCheck.increment`/`AgentCheck.decrement` are deprecated, please use "
                "`AgentCheck.gauge` or `AgentCheck.count` instead, with a different metric name",
            ],
            'device_name': [
                False,
                "DEPRECATION NOTICE: `device_name` is deprecated, please use a `device:` "
                "tag in the `tags` list instead",
            ],
            'in_developer_mode': [
                False,
                "DEPRECATION NOTICE: `in_developer_mode` is deprecated, please stop using it.",
            ],
            'no_proxy': [
                False,
                "DEPRECATION NOTICE: The `no_proxy` config option has been renamed "
                "to `skip_proxy` and will be removed in Agent version 6.13.",
            ],
        }

        # Setup metric limits
        try:
            metric_limit = self.instances[0].get("max_returned_metrics", self.DEFAULT_METRIC_LIMIT)
            # Do not allow to disable limiting if the class has set a non-zero default value
            if metric_limit == 0 and self.DEFAULT_METRIC_LIMIT > 0:
                metric_limit = self.DEFAULT_METRIC_LIMIT
                self.warning(
                    "Setting max_returned_metrics to zero is not allowed, "
                    "reverting to the default of {} metrics".format(self.DEFAULT_METRIC_LIMIT)
                )
        except Exception:
            metric_limit = self.DEFAULT_METRIC_LIMIT
        if metric_limit > 0:
            self.metric_limiter = Limiter(self.name, "metrics", metric_limit, self.warning)

    @staticmethod
    def load_config(yaml_str):
        """
        Convenience wrapper to ease programmatic use of this class from the C API.
        """
        return yaml.safe_load(yaml_str)

    @property
    def http(self):
        if self._http is None:
            self._http = RequestsWrapper(self.instance or {}, self.init_config, self.HTTP_CONFIG_REMAPPER, self.log)

        return self._http

    @property
    def in_developer_mode(self):
        self._log_deprecation('in_developer_mode')
        return False

    def get_instance_proxy(self, instance, uri, proxies=None):
        # TODO: Remove with Agent 5
        proxies = proxies if proxies is not None else self.proxies.copy()

        deprecated_skip = instance.get('no_proxy', None)
        skip = is_affirmative(instance.get('skip_proxy', not self._use_agent_proxy)) or is_affirmative(deprecated_skip)

        if deprecated_skip is not None:
            self._log_deprecation('no_proxy')

        return config_proxy_skip(proxies, uri, skip)

    def _context_uid(self, mtype, name, tags=None, hostname=None):
        return '{}-{}-{}-{}'.format(mtype, name, tags if tags is None else hash(frozenset(tags)), hostname)

    def _format_namespace(self, s):
        if self.__NAMESPACE__:
            return '{}.{}'.format(self.__NAMESPACE__, ensure_bytes(s))

        return ensure_bytes(s)

    def _submit_metric(self, mtype, name, value, tags=None, hostname=None, device_name=None):
        if value is None:
            # ignore metric sample
            return

        tags = self._normalize_tags_type(tags, device_name, name)
        if hostname is None:
            hostname = b''

        if self.metric_limiter:
            if mtype in ONE_PER_CONTEXT_METRIC_TYPES:
                # Fast path for gauges, rates, monotonic counters, assume one set of tags per call
                if self.metric_limiter.is_reached():
                    return
            else:
                # Other metric types have a legit use case for several calls per set of tags, track unique sets of tags
                context = self._context_uid(mtype, name, tags, hostname)
                if self.metric_limiter.is_reached(context):
                    return

        try:
            value = float(value)
        except ValueError:
            err_msg = "Metric: {} has non float value: {}. " "Only float values can be submitted as metrics.".format(
                repr(name), repr(value)
            )
            if using_stub_aggregator:
                raise ValueError(err_msg)
            self.warning(err_msg)
            return

        aggregator.submit_metric(self, self.check_id, mtype, self._format_namespace(name), value, tags, hostname)

    def gauge(self, name, value, tags=None, hostname=None, device_name=None):
        self._submit_metric(aggregator.GAUGE, name, value, tags=tags, hostname=hostname, device_name=device_name)

    def count(self, name, value, tags=None, hostname=None, device_name=None):
        self._submit_metric(aggregator.COUNT, name, value, tags=tags, hostname=hostname, device_name=device_name)

    def monotonic_count(self, name, value, tags=None, hostname=None, device_name=None):
        self._submit_metric(
            aggregator.MONOTONIC_COUNT, name, value, tags=tags, hostname=hostname, device_name=device_name
        )

    def rate(self, name, value, tags=None, hostname=None, device_name=None):
        self._submit_metric(aggregator.RATE, name, value, tags=tags, hostname=hostname, device_name=device_name)

    def histogram(self, name, value, tags=None, hostname=None, device_name=None):
        self._submit_metric(aggregator.HISTOGRAM, name, value, tags=tags, hostname=hostname, device_name=device_name)

    def historate(self, name, value, tags=None, hostname=None, device_name=None):
        self._submit_metric(aggregator.HISTORATE, name, value, tags=tags, hostname=hostname, device_name=device_name)

    def increment(self, name, value=1, tags=None, hostname=None, device_name=None):
        self._log_deprecation("increment")
        self._submit_metric(aggregator.COUNTER, name, value, tags=tags, hostname=hostname, device_name=device_name)

    def decrement(self, name, value=-1, tags=None, hostname=None, device_name=None):
        self._log_deprecation("increment")
        self._submit_metric(aggregator.COUNTER, name, value, tags=tags, hostname=hostname, device_name=device_name)

    def _log_deprecation(self, deprecation_key):
        """
        Logs a deprecation notice at most once per AgentCheck instance, for the pre-defined `deprecation_key`
        """
        if not self._deprecations[deprecation_key][0]:
            self.log.warning(self._deprecations[deprecation_key][1])
            self._deprecations[deprecation_key][0] = True

    def service_check(self, name, status, tags=None, hostname=None, message=None):
        tags = self._normalize_tags_type(tags)
        if hostname is None:
            hostname = b''
        if message is None:
            message = b''
        else:
            message = ensure_bytes(message)

        aggregator.submit_service_check(
            self, self.check_id, self._format_namespace(name), status, tags, hostname, message
        )

    def event(self, event):
        # Enforce types of some fields, considerably facilitates handling in go bindings downstream
        for key, value in list(iteritems(event)):
            # transform the unicode objects to plain strings with utf-8 encoding
            if isinstance(value, text_type):
                try:
                    event[key] = event[key].encode('utf-8')
                except UnicodeError:
                    self.log.warning(
                        "Error encoding unicode field '%s' to utf-8 encoded string, can't submit event", key
                    )
                    return

        if event.get('tags'):
            event['tags'] = self._normalize_tags_type(event['tags'])
        if event.get('timestamp'):
            event['timestamp'] = int(event['timestamp'])
        if event.get('aggregation_key'):
            event['aggregation_key'] = ensure_bytes(event['aggregation_key'])

        if self.__NAMESPACE__:
            event.setdefault('source_type_name', self.__NAMESPACE__)

        aggregator.submit_event(self, self.check_id, event)

    # TODO(olivier): implement service_metadata if it's worth it
    def service_metadata(self, meta_name, value):
        pass

    def check(self, instance):
        raise NotImplementedError

    def normalize(self, metric, prefix=None, fix_case=False):
        """
        Turn a metric into a well-formed metric name
        prefix.b.c
        :param metric The metric name to normalize
        :param prefix A prefix to to add to the normalized name, default None
        :param fix_case A boolean, indicating whether to make sure that the metric name returned is in "snake_case"
        """
        if isinstance(metric, text_type):
            metric = unicodedata.normalize('NFKD', metric).encode('ascii', 'ignore')

        if fix_case:
            name = self.convert_to_underscore_separated(metric)
            if prefix is not None:
                prefix = self.convert_to_underscore_separated(prefix)
        else:
            name = re.sub(br"[,\+\*\-/()\[\]{}\s]", b"_", metric)
        # Eliminate multiple _
        name = re.sub(br"__+", b"_", name)
        # Don't start/end with _
        name = re.sub(br"^_", b"", name)
        name = re.sub(br"_$", b"", name)
        # Drop ._ and _.
        name = re.sub(br"\._", b".", name)
        name = re.sub(br"_\.", b".", name)

        if prefix is not None:
            return ensure_bytes(prefix) + b"." + name
        else:
            return name

    FIRST_CAP_RE = re.compile(br'(.)([A-Z][a-z]+)')
    ALL_CAP_RE = re.compile(br'([a-z0-9])([A-Z])')
    METRIC_REPLACEMENT = re.compile(br'([^a-zA-Z0-9_.]+)|(^[^a-zA-Z]+)')
    DOT_UNDERSCORE_CLEANUP = re.compile(br'_*\._*')

    def convert_to_underscore_separated(self, name):
        """
        Convert from CamelCase to camel_case
        And substitute illegal metric characters
        """
        metric_name = self.FIRST_CAP_RE.sub(br'\1_\2', ensure_bytes(name))
        metric_name = self.ALL_CAP_RE.sub(br'\1_\2', metric_name).lower()
        metric_name = self.METRIC_REPLACEMENT.sub(br'_', metric_name)
        return self.DOT_UNDERSCORE_CLEANUP.sub(br'.', metric_name).strip(b'_')

    def set_external_tags(self, external_tags):
        # Example of external_tags format
        # [
        #     ('hostname', {'src_name': ['test:t1']}),
        #     ('hostname2', {'src2_name': ['test2:t3']})
        # ]

        try:
            for _, source_map in external_tags:
                for src_name, tags in iteritems(source_map):
                    source_map[src_name] = self._normalize_tags_type(tags)
            datadog_agent.set_external_tags(external_tags)
        except IndexError:
            self.log.exception('Unexpected external tags format: {}'.format(external_tags))
            raise

    def _normalize_tags_type(self, tags, device_name=None, metric_name=None):
        """
        Normalize tags contents and type:
        - append `device_name` as `device:` tag
        - normalize tags type
        - doesn't mutate the passed list, returns a new list
        """
        normalized_tags = []

        if device_name:
            self._log_deprecation("device_name")
            device_tag = self._to_bytes("device:{}".format(device_name))
            if device_tag is None:
                self.log.warning(
                    'Error encoding device name `{}` to utf-8 for metric `{}`, ignoring tag'.format(
                        repr(device_name), repr(metric_name)
                    )
                )
            else:
                normalized_tags.append(device_tag)

        if tags is not None:
            for tag in tags:
                if tag is None:
                    continue
                encoded_tag = self._to_bytes(tag)
                if encoded_tag is None:
                    self.log.warning(
                        'Error encoding tag `{}` to utf-8 for metric `{}`, ignoring tag'.format(
                            repr(tag), repr(metric_name)
                        )
                    )
                    continue
                normalized_tags.append(encoded_tag)

        return normalized_tags

    def _to_bytes(self, data):
        """
        Normalize a text data to bytes (type `bytes`) so that the go bindings can
        handle it easily.
        """
        # TODO: On Python 3, move this `if` line to the `except` branch
        # as the common case will indeed no longer be bytes.
        if not isinstance(data, bytes):
            try:
                return data.encode('utf-8')
            except Exception:
                return None

        return data

    def warning(self, warning_message):
        warning_message = ensure_bytes(warning_message)

        frame = inspect.currentframe().f_back
        lineno = frame.f_lineno
        filename = frame.f_code.co_filename
        # only log the last part of the filename, not the full path
        filename = basename(filename)

        self.log.warning(warning_message, extra={'_lineno': lineno, '_filename': filename})
        self.warnings.append(warning_message)

    def get_warnings(self):
        """
        Return the list of warnings messages to be displayed in the info page
        """
        warnings = self.warnings
        self.warnings = []
        return warnings

    def run(self):
        try:
            instance = copy.deepcopy(self.instances[0])

            if 'set_breakpoint' in self.init_config:
                enter_pdb(self.check, line=self.init_config['set_breakpoint'], args=(instance,))
            else:
                self.check(instance)

            result = b''
        except Exception as e:
            result = json.dumps([{"message": str(e), "traceback": traceback.format_exc()}])
        finally:
            if self.metric_limiter:
                self.metric_limiter.reset()

        return result

    def _get_requests_proxy(self):
        # TODO: Remove with Agent 5
        no_proxy_settings = {"http": None, "https": None, "no": []}

        # First we read the proxy configuration from datadog.conf
        proxies = self.agentConfig.get('proxy', datadog_agent.get_config('proxy'))
        if proxies:
            proxies = proxies.copy()

        # requests compliant dict
        if proxies and 'no_proxy' in proxies:
            proxies['no'] = proxies.pop('no_proxy')

        return proxies if proxies else no_proxy_settings


if PY3:
    AgentCheck = __AgentCheckPy3
    del __AgentCheckPy2
else:
    AgentCheck = __AgentCheckPy2
    del __AgentCheckPy3
