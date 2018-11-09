# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import defaultdict
import logging
import re
import json
import copy
import traceback
import unicodedata

from six import iteritems, text_type

try:
    import datadog_agent
    from ..log import init_logging
    init_logging()
except ImportError:
    from ..stubs import datadog_agent

try:
    import aggregator
    using_stub_aggregator = False
except ImportError:
    from ..stubs import aggregator
    using_stub_aggregator = True

from ..config import is_affirmative
from ..utils.common import ensure_bytes
from ..utils.proxy import config_proxy_skip
from ..utils.limiter import Limiter


# Metric types for which it's only useful to submit once per set of tags
ONE_PER_CONTEXT_METRIC_TYPES = [
    aggregator.GAUGE,
    aggregator.RATE,
    aggregator.MONOTONIC_COUNT,
]


class AgentCheck(object):
    """
    The base class for any Agent based integrations
    """
    OK, WARNING, CRITICAL, UNKNOWN = (0, 1, 2, 3)

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

        # `self.hostname` is deprecated, use `datadog_agent.get_hostname()` instead
        self.hostname = datadog_agent.get_hostname()

        # the agent5 'AgentCheck' setup a log attribute.
        self.log = logging.getLogger('%s.%s' % (__name__, self.name))

        # Set proxy settings
        self.proxies = self._get_requests_proxy()
        if not self.init_config:
            self._use_agent_proxy = True
        else:
            self._use_agent_proxy = is_affirmative(
                self.init_config.get("use_agent_proxy", True))

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
                "to `skip_proxy` and will be removed in a future release.",
            ],
        }

        # Setup metric limits
        try:
            metric_limit = self.instances[0].get("max_returned_metrics", self.DEFAULT_METRIC_LIMIT)
            # Do not allow to disable limiting if the class has set a non-zero default value
            if metric_limit == 0 and self.DEFAULT_METRIC_LIMIT > 0:
                metric_limit = self.DEFAULT_METRIC_LIMIT
                self.warning("Setting max_returned_metrics to zero is not allowed, "
                             "reverting to the default of {} metrics".format(self.DEFAULT_METRIC_LIMIT))
        except Exception:
            metric_limit = self.DEFAULT_METRIC_LIMIT
        if metric_limit > 0:
            self.metric_limiter = Limiter(self.name, "metrics", metric_limit, self.warning)

    @property
    def in_developer_mode(self):
        self._log_deprecation('in_developer_mode')
        return False

    def get_instance_proxy(self, instance, uri, proxies=None):
        proxies = proxies if proxies is not None else self.proxies.copy()

        deprecated_skip = instance.get('no_proxy', None)
        skip = (
            is_affirmative(instance.get('skip_proxy', not self._use_agent_proxy)) or
            is_affirmative(deprecated_skip)
        )

        if deprecated_skip is not None:
            self._log_deprecation('no_proxy')

        return config_proxy_skip(proxies, uri, skip)

    def _context_uid(mtype, name, value, tags=None, hostname=None):
        return '{}-{}-{}-{}'.format(mtype, name, tags if tags is None else hash(frozenset(tags)), hostname)

    def _submit_metric(self, mtype, name, value, tags=None, hostname=None, device_name=None):
        if value is None:
            # ignore metric sample
            return

        tags = self._normalize_tags(tags, device_name)
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
            err_msg = (
                "Metric: {} has non float value: {}. "
                "Only float values can be submitted as metrics.".format(repr(name), repr(value))
            )
            if using_stub_aggregator:
                raise ValueError(err_msg)
            self.warning(err_msg)
            return

        aggregator.submit_metric(self, self.check_id, mtype, ensure_bytes(name), value, tags, hostname)

    def gauge(self, name, value, tags=None, hostname=None, device_name=None):
        self._submit_metric(aggregator.GAUGE, name, value, tags=tags, hostname=hostname, device_name=device_name)

    def count(self, name, value, tags=None, hostname=None, device_name=None):
        self._submit_metric(aggregator.COUNT, name, value, tags=tags, hostname=hostname, device_name=device_name)

    def monotonic_count(self, name, value, tags=None, hostname=None, device_name=None):
        self._submit_metric(aggregator.MONOTONIC_COUNT, name, value, tags=tags, hostname=hostname,
                            device_name=device_name)

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

        aggregator.submit_service_check(self, self.check_id, ensure_bytes(name), status, tags, hostname, message)

    def event(self, event):
        # Enforce types of some fields, considerably facilitates handling in go bindings downstream
        for key, value in list(iteritems(event)):
            # transform the unicode objects to plain strings with utf-8 encoding
            if isinstance(value, text_type):
                try:
                    event[key] = event[key].encode('utf-8')
                except UnicodeError:
                    self.log.warning("Error encoding unicode field '%s' to utf-8 encoded string, can't submit event",
                                     key)
                    return
        if event.get('tags'):
            event['tags'] = self._normalize_tags_type(event['tags'])
        if event.get('timestamp'):
            event['timestamp'] = int(event['timestamp'])
        if event.get('aggregation_key'):
            event['aggregation_key'] = ensure_bytes(event['aggregation_key'])
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
            metric_name = unicodedata.normalize('NFKD', metric).encode('ascii', 'ignore')
        else:
            metric_name = metric

        if fix_case:
            name = self.convert_to_underscore_separated(metric_name)
            if prefix is not None:
                prefix = self.convert_to_underscore_separated(prefix)
        else:
            name = re.sub(br"[,\+\*\-/()\[\]{}\s]", b"_", metric_name)
        # Eliminate multiple _
        name = re.sub(br"__+", b"_", name)
        # Don't start/end with _
        name = re.sub(br"^_", b"", name)
        name = re.sub(br"_$", b"", name)
        # Drop ._ and _.
        name = re.sub(br"\._", b".", name)
        name = re.sub(br"_\.", b".", name)

        if prefix is not None:
            return prefix + "." + name
        else:
            return name

    FIRST_CAP_RE = re.compile('(.)([A-Z][a-z]+)')
    ALL_CAP_RE = re.compile('([a-z0-9])([A-Z])')
    METRIC_REPLACEMENT = re.compile(r'([^a-zA-Z0-9_.]+)|(^[^a-zA-Z]+)')
    DOT_UNDERSCORE_CLEANUP = re.compile(r'_*\._*')

    def convert_to_underscore_separated(self, name):
        """
        Convert from CamelCase to camel_case
        And substitute illegal metric characters
        """
        metric_name = self.FIRST_CAP_RE.sub(r'\1_\2', name)
        metric_name = self.ALL_CAP_RE.sub(r'\1_\2', metric_name).lower()
        metric_name = self.METRIC_REPLACEMENT.sub('_', metric_name)
        return self.DOT_UNDERSCORE_CLEANUP.sub('.', metric_name).strip('_')

    def _normalize_tags(self, tags, device_name):
        """
        Normalize tags:
        - append `device_name` as `device:` tag
        - normalize tags to type `str`
        - always return a list
        """
        normalized_tags = self._normalize_tags_type(tags)

        if device_name:
            self._log_deprecation("device_name")
            normalized_tags.append("device:%s" % device_name)

        return normalized_tags

    def _normalize_tags_type(self, tags):
        """
        Normalize all the tags to bytes (type `bytes`) so that the go bindings can handle them easily
        Doesn't mutate the passed list, returns a new list
        """
        normalized_tags = []
        if tags is not None:
            for tag in tags:
                # TODO: On Python 3, move this `if` line to the `except` branch
                # as the common case will indeed no longer be bytes.
                if not isinstance(tag, bytes):
                    try:
                        tag = tag.encode('utf-8')
                    except Exception:
                        self.log.warning('Error encoding tag to utf-8 encoded string, ignoring tag')
                        continue

                normalized_tags.append(tag)

        return normalized_tags

    def warning(self, warning_message):
        warning_message = str(warning_message)
        self.log.warning(warning_message)
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
            self.check(copy.deepcopy(self.instances[0]))
            result = b''
        except Exception as e:
            result = json.dumps([
                {
                    "message": str(e),
                    "traceback": traceback.format_exc(),
                }
            ])
        finally:
            if self.metric_limiter:
                self.metric_limiter.reset()

        return result

    def _get_requests_proxy(self):
        no_proxy_settings = {
            "http": None,
            "https": None,
            "no": [],
        }

        # First we read the proxy configuration from datadog.conf
        proxies = self.agentConfig.get('proxy', datadog_agent.get_config('proxy'))
        if proxies:
            proxies = proxies.copy()

        # requests compliant dict
        if proxies and 'no_proxy' in proxies:
            proxies['no'] = proxies.pop('no_proxy')

        return proxies if proxies else no_proxy_settings
