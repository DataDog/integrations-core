# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import importlib
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
from ..utils.common import ensure_bytes, ensure_unicode, to_string
from ..utils.http import RequestsWrapper
from ..utils.limiter import Limiter
from ..utils.proxy import config_proxy_skip

try:
    import datadog_agent
    from ..log import CheckLoggingAdapter, init_logging

    init_logging()
except ImportError:
    from ..stubs import datadog_agent
    from ..stubs.log import CheckLoggingAdapter, init_logging

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


class __AgentCheck(object):
    """The base class for any Agent based integrations.

    :cvar DEFAULT_METRIC_LIMIT: allows to set a limit on the number of metric name and tags combination
        this check can send per run. This is useful for checks that have an unbounded
        number of tag values that depend on the input payload.
        The logic counts one set of tags per gauge/rate/monotonic_count call, and deduplicates
        sets of tags for other metric types. The first N sets of tags in submission order will
        be sent to the aggregator, the rest are dropped. The state is reset after each run.
        See https://github.com/DataDog/integrations-core/pull/2093 for more informations.
    :ivar log: is a logger instance that prints to the Agent's main log file. You can set the
        log level in the Agent config file 'datadog.yaml'.
    """

    # If defined, this will be the prefix of every metric/service check and the source type of events
    __NAMESPACE__ = ''

    OK, WARNING, CRITICAL, UNKNOWN = ServiceCheck

    HTTP_CONFIG_REMAPPER = None  # Used by `self.http` RequestsWrapper
    FIRST_CAP_RE = re.compile(br'(.)([A-Z][a-z]+)')
    ALL_CAP_RE = re.compile(br'([a-z0-9])([A-Z])')
    METRIC_REPLACEMENT = re.compile(br'([^a-zA-Z0-9_.]+)|(^[^a-zA-Z]+)')
    DOT_UNDERSCORE_CLEANUP = re.compile(br'_*\._*')
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, *args, **kwargs):
        """In general, you don't need to and you should not override anything from the base
        class except the :py:meth:`check` method but sometimes it might be useful for a Check to
        have its own constructor.

        When overriding `__init__` you have to remember that, depending on the configuration,
        the Agent might create several different Check instances and the method would be
        called as many times.

        :warning: when loading a Custom check, the Agent will inspect the module searching
            for a subclass of `AgentCheck`. If such a class exists but has been derived in
            turn, it'll be ignored - **you should never derive from an existing Check**.

        :param str name: the name of the check.
        :param dict init_config: the 'init_config' section of the configuration.
        :param list instances: a one-element list containing the instance options from the
                configuration file (a list is used to keep backward compatibility with
                older versions of the Agent).
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

        logger = logging.getLogger('{}.{}'.format(__name__, self.name))
        self.log = CheckLoggingAdapter(logger, self)

        # Provides logic to yield consistent network behavior based on user configuration.
        # Only new checks or checks on Agent 6.13+ can and should use this for HTTP requests.
        self._http = None

        # Save the dynamically detected integration version
        self._check_version = None

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
    def check_version(self):
        if self._check_version is None:
            # 'datadog_checks.<PACKAGE>.<MODULE>...'
            module_parts = self.__module__.split('.')
            package_path = '.'.join(module_parts[:2])
            package = importlib.import_module(package_path)

            # Provide a default just in case
            self._check_version = getattr(package, '__version__', '0.0.0')

        return self._check_version

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

    def submit_histogram_bucket(self, name, value, lower_bound, upper_bound, monotonic, hostname, tags):
        if value is None:
            # ignore metric sample
            return

        # make sure the value (bucket count) is an integer
        try:
            value = int(value)
        except ValueError:
            err_msg = 'Histogram: {} has non integer value: {}. Only integer are valid bucket values (count).'.format(
                repr(name), repr(value)
            )
            if using_stub_aggregator:
                raise ValueError(err_msg)
            self.warning(err_msg)
            return

        tags = self._normalize_tags_type(tags, metric_name=name)
        if hostname is None:
            hostname = ''

        aggregator.submit_histogram_bucket(
            self, self.check_id, name, value, lower_bound, upper_bound, monotonic, hostname, tags
        )

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
                repr(name), repr(value)
            )
            if using_stub_aggregator:
                raise ValueError(err_msg)
            self.warning(err_msg)
            return

        aggregator.submit_metric(self, self.check_id, mtype, self._format_namespace(name), value, tags, hostname)

    def gauge(self, name, value, tags=None, hostname=None, device_name=None):
        """Sample a gauge metric.

        :param str name: the name of the metric.
        :param float value: the value for the metric.
        :param list tags: (optional) a list of tags to associate with this metric.
        :param str hostname: (optional) a hostname to associate with this metric. Defaults to the current host.
        :param str device_name: **deprecated** add a tag in the form :code:`device:<device_name>` to the :code:`tags`
            list instead.
        """
        self._submit_metric(aggregator.GAUGE, name, value, tags=tags, hostname=hostname, device_name=device_name)

    def count(self, name, value, tags=None, hostname=None, device_name=None):
        """Sample a raw count metric.

        :param str name: the name of the metric.
        :param float value: the value for the metric.
        :param list tags: (optional) a list of tags to associate with this metric.
        :param str hostname: (optional) a hostname to associate with this metric. Defaults to the current host.
        :param str device_name: **deprecated** add a tag in the form :code:`device:<device_name>` to the :code:`tags`
            list instead.
        """
        self._submit_metric(aggregator.COUNT, name, value, tags=tags, hostname=hostname, device_name=device_name)

    def monotonic_count(self, name, value, tags=None, hostname=None, device_name=None):
        """Sample an increasing counter metric.

        :param str name: the name of the metric.
        :param float value: the value for the metric.
        :param list tags: (optional) a list of tags to associate with this metric.
        :param str hostname: (optional) a hostname to associate with this metric. Defaults to the current host.
        :param str device_name: **deprecated** add a tag in the form :code:`device:<device_name>` to the :code:`tags`
            list instead.
        """
        self._submit_metric(
            aggregator.MONOTONIC_COUNT, name, value, tags=tags, hostname=hostname, device_name=device_name
        )

    def rate(self, name, value, tags=None, hostname=None, device_name=None):
        """Sample a point, with the rate calculated at the end of the check.

        :param str name: the name of the metric.
        :param float value: the value for the metric.
        :param list tags: (optional) a list of tags to associate with this metric.
        :param str hostname: (optional) a hostname to associate with this metric. Defaults to the current host.
        :param str device_name: **deprecated** add a tag in the form :code:`device:<device_name>` to the :code:`tags`
            list instead.
        """
        self._submit_metric(aggregator.RATE, name, value, tags=tags, hostname=hostname, device_name=device_name)

    def histogram(self, name, value, tags=None, hostname=None, device_name=None):
        """Sample a histogram metric.

        :param str name: the name of the metric.
        :param float value: the value for the metric.
        :param list tags: (optional) a list of tags to associate with this metric.
        :param str hostname: (optional) a hostname to associate with this metric. Defaults to the current host.
        :param str device_name: **deprecated** add a tag in the form :code:`device:<device_name>` to the :code:`tags`
            list instead.
        """
        self._submit_metric(aggregator.HISTOGRAM, name, value, tags=tags, hostname=hostname, device_name=device_name)

    def historate(self, name, value, tags=None, hostname=None, device_name=None):
        """Sample a histogram based on rate metrics.

        :param str name: the name of the metric.
        :param float value: the value for the metric.
        :param list tags: (optional) a list of tags to associate with this metric.
        :param str hostname: (optional) a hostname to associate with this metric. Defaults to the current host.
        :param str device_name: **deprecated** add a tag in the form :code:`device:<device_name>` to the :code:`tags`
            list instead.
        """
        self._submit_metric(aggregator.HISTORATE, name, value, tags=tags, hostname=hostname, device_name=device_name)

    def increment(self, name, value=1, tags=None, hostname=None, device_name=None):
        """Increment a counter metric.

        :param str name: the name of the metric.
        :param float value: the value for the metric.
        :param list tags: (optional) a list of tags to associate with this metric.
        :param str hostname: (optional) a hostname to associate with this metric. Defaults to the current host.
        :param str device_name: **deprecated** add a tag in the form :code:`device:<device_name>` to the :code:`tags`
            list instead.
        """
        self._log_deprecation('increment')
        self._submit_metric(aggregator.COUNTER, name, value, tags=tags, hostname=hostname, device_name=device_name)

    def decrement(self, name, value=-1, tags=None, hostname=None, device_name=None):
        """Decrement a counter metric.

        :param str name: the name of the metric.
        :param float value: the value for the metric.
        :param list tags: (optional) a list of tags to associate with this metric.
        :param str hostname: (optional) a hostname to associate with this metric. Defaults to the current host.
        :param str device_name: **deprecated** add a tag in the form :code:`device:<device_name>` to the :code:`tags`
            list instead.
        """
        self._log_deprecation('increment')
        self._submit_metric(aggregator.COUNTER, name, value, tags=tags, hostname=hostname, device_name=device_name)

    def service_check(self, name, status, tags=None, hostname=None, message=None):
        """Send the status of a service.

        :param str name: the name of the service check.
        :param status: a constant describing the service status.
        :type status: :py:class:`datadog_checks.base.constants.ServiceCheck`
        :param list tags: (optional) a list of tags to associate with this check.
        :param str message: (optional) additional information or a description of why this status occurred.
        """
        tags = self._normalize_tags_type(tags)
        if hostname is None:
            hostname = ''
        if message is None:
            message = ''
        else:
            message = to_string(message)

        aggregator.submit_service_check(
            self, self.check_id, self._format_namespace(name), status, tags, hostname, message
        )

    def _log_deprecation(self, deprecation_key):
        """
        Logs a deprecation notice at most once per AgentCheck instance, for the pre-defined `deprecation_key`
        """
        if not self._deprecations[deprecation_key][0]:
            self.log.warning(self._deprecations[deprecation_key][1])
            self._deprecations[deprecation_key][0] = True

    # TODO(olivier): implement service_metadata if it's worth it
    def service_metadata(self, meta_name, value):
        pass

    def set_external_tags(self, external_tags):
        # Example of external_tags format
        # [
        #     ('hostname', {'src_name': ['test:t1']}),
        #     ('hostname2', {'src2_name': ['test2:t3']})
        # ]
        try:
            new_tags = []
            for hostname, source_map in external_tags:
                new_tags.append((to_string(hostname), source_map))
                for src_name, tags in iteritems(source_map):
                    source_map[src_name] = self._normalize_tags_type(tags)
            datadog_agent.set_external_tags(new_tags)
        except IndexError:
            self.log.exception('Unexpected external tags format: {}'.format(external_tags))
            raise

    def convert_to_underscore_separated(self, name):
        """
        Convert from CamelCase to camel_case
        And substitute illegal metric characters
        """
        metric_name = self.FIRST_CAP_RE.sub(br'\1_\2', ensure_bytes(name))
        metric_name = self.ALL_CAP_RE.sub(br'\1_\2', metric_name).lower()
        metric_name = self.METRIC_REPLACEMENT.sub(br'_', metric_name)
        return self.DOT_UNDERSCORE_CLEANUP.sub(br'.', metric_name).strip(b'_')

    def warning(self, warning_message):
        """Log a warning message and display it in the Agent's status page.

        :param str warning_message: the warning message.
        """
        warning_message = to_string(warning_message)

        frame = inspect.currentframe().f_back
        lineno = frame.f_lineno
        # only log the last part of the filename, not the full path
        filename = basename(frame.f_code.co_filename)

        self.log.warning(warning_message, extra={'_lineno': lineno, '_filename': filename, '_check_id': self.check_id})
        self.warnings.append(warning_message)

    def get_warnings(self):
        """
        Return the list of warnings messages to be displayed in the info page
        """
        warnings = self.warnings
        self.warnings = []
        return warnings

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

    def _format_namespace(self, s):
        if self.__NAMESPACE__:
            return '{}.{}'.format(self.__NAMESPACE__, to_string(s))

        return to_string(s)

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

        return to_string(name)

    def check(self, instance):
        raise NotImplementedError

    def run(self):
        try:
            instance = copy.deepcopy(self.instances[0])

            if 'set_breakpoint' in self.init_config:
                from ..utils.agent.debug import enter_pdb

                enter_pdb(self.check, line=self.init_config['set_breakpoint'], args=(instance,))
            elif 'profile_memory' in self.init_config or datadog_agent.tracemalloc_enabled():
                from ..utils.agent.memory import profile_memory

                metrics = profile_memory(
                    self.check, self.init_config, namespaces=self.check_id.split(':', 1), args=(instance,)
                )

                tags = ['check_name:{}'.format(self.name), 'check_version:{}'.format(self.check_version)]
                for m in metrics:
                    self.gauge(m.name, m.value, tags=tags)
            else:
                self.check(instance)

            result = ''
        except Exception as e:
            result = json.dumps([{'message': str(e), 'traceback': traceback.format_exc()}])
        finally:
            if self.metric_limiter:
                self.metric_limiter.reset()

        return result


class __AgentCheckPy3(__AgentCheck):
    """
    Python3 version of the __AgentCheck base class, overrides few methods to
    add compatibility with Python3.
    """

    def event(self, event):
        """Send an event.

        An event is a dictionary with the following keys and data types:

        .. code:: python

            {
                "timestamp": int,        # the epoch timestamp for the event
                "event_type": str,       # the event name
                "api_key": str,          # the api key for your account
                "msg_title": str,        # the title of the event
                "msg_text": str,         # the text body of the event
                "aggregation_key": str,  # a key to use for aggregating events
                "alert_type": str,       # (optional) one of ('error', 'warning', 'success', 'info'), defaults to 'info'
                "source_type_name": str, # (optional) the source type name
                "host": str,             # (optional) the name of the host
                "tags": list,            # (optional) a list of tags to associate with this event
                "priority": str,         # (optional) specifies the priority of the event ("normal" or "low")
            }

        :param ev event: the event to be sent.
        """
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


class __AgentCheckPy2(__AgentCheck):
    """
    Python2 version of the __AgentCheck base class, overrides few methods to
    add compatibility with Python2.
    """

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


AgentCheck = __AgentCheckPy3 if PY3 else __AgentCheckPy2
