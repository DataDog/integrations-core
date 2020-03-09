# (C) Datadog, Inc. 2018-present
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
from collections import defaultdict, deque
from os.path import basename

import yaml
from six import binary_type, iteritems, text_type

from ..config import is_affirmative
from ..constants import ServiceCheck
from ..utils.agent.utils import should_profile_memory
from ..utils.common import ensure_bytes, to_string
from ..utils.http import RequestsWrapper
from ..utils.limiter import Limiter
from ..utils.metadata import MetadataManager
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


class AgentCheck(object):
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

    # Used by `self.http` for an instance of RequestsWrapper
    HTTP_CONFIG_REMAPPER = None

    # Used by `self.set_metadata` for an instance of MetadataManager
    #
    # This is a mapping of metadata names to functions. When you call `self.set_metadata(name, value, **options)`,
    # if `name` is in this mapping then the corresponding function will be called with the `value`, and the
    # return value(s) will be sent instead.
    #
    # Transformer functions must satisfy the following signature:
    #
    #    def transform_<NAME>(value: Any, options: dict) -> Union[str, Dict[str, str]]:
    #
    # If the return type is a string, then it will be sent as the value for `name`. If the return type is
    # a mapping type, then each key will be considered a `name` and will be sent with its (str) value.
    METADATA_TRANSFORMERS = None

    # Default fields to whitelist for metadata submission
    METADATA_DEFAULT_CONFIG_INIT_CONFIG = None
    METADATA_DEFAULT_CONFIG_INSTANCE = None

    FIRST_CAP_RE = re.compile(br'(.)([A-Z][a-z]+)')
    ALL_CAP_RE = re.compile(br'([a-z0-9])([A-Z])')
    METRIC_REPLACEMENT = re.compile(br'([^a-zA-Z0-9_.]+)|(^[^a-zA-Z]+)')
    TAG_REPLACEMENT = re.compile(br'[,\+\*\-/()\[\]{}\s]')
    MULTIPLE_UNDERSCORE_CLEANUP = re.compile(br'__+')
    DOT_UNDERSCORE_CLEANUP = re.compile(br'_*\._*')
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, *args, **kwargs):
        """In general, you don't need to and you should not override anything from the base
        class except the :py:meth:`check` method but sometimes it might be useful for a Check to
        have its own constructor.

        When overriding `__init__` you have to remember that, depending on the configuration,
        the Agent might create several different Check instances and the method would be
        called as many times.

        Agent 6,7 signature:

            AgentCheck(name, init_config, instances)    # instances contain only 1 instance
            AgentCheck.check(instance)

        Agent 8 signature:

            AgentCheck(name, init_config, instance)     # one instance
            AgentCheck.check()                          # no more instance argument for check method

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

        if len(args) > 0:
            self.name = args[0]
        if len(args) > 1:
            self.init_config = args[1]
        if len(args) > 2:
            # agent pass instances as tuple but in test we are usually using list, so we are testing for both
            if len(args) > 3 or not isinstance(args[2], (list, tuple)) or 'instances' in kwargs:
                # old-style init: the 3rd argument is `agentConfig`
                self.agentConfig = args[2]
                if len(args) > 3:
                    self.instances = args[3]
            else:
                # new-style init: the 3rd argument is `instances`
                self.instances = args[2]

        # NOTE: Agent 6+ should pass exactly one instance... But we are not abiding by that rule on our side
        # everywhere just yet. It's complicated... See: https://github.com/DataDog/integrations-core/pull/5573
        self.instance = self.instances[0] if self.instances else None

        # `self.hostname` is deprecated, use `datadog_agent.get_hostname()` instead
        self.hostname = datadog_agent.get_hostname()

        logger = logging.getLogger('{}.{}'.format(__name__, self.name))
        self.log = CheckLoggingAdapter(logger, self)

        # Provides logic to yield consistent network behavior based on user configuration.
        # Only new checks or checks on Agent 6.13+ can and should use this for HTTP requests.
        self._http = None

        # Used for sending metadata via Go bindings
        self._metadata_manager = None

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
            'service_tag': [
                False,
                (
                    'DEPRECATION NOTICE: The `service` tag is deprecated and has been renamed to `%s`. '
                    'Set `disable_legacy_service_tag` to `true` to disable this warning. '
                    'The default will become `true` and cannot be changed in Agent version 8.'
                ),
            ],
        }

        # Setup metric limits
        self.metric_limiter = self._get_metric_limiter(self.name, instance=self.instance)

        # Functions that will be called exactly once (if successful) before the first check run
        self.check_initializations = deque([self.send_config_metadata])

    def _get_metric_limiter(self, name, instance=None):
        limit = self._get_metric_limit(instance=instance)

        if limit > 0:
            return Limiter(name, 'metrics', limit, self.warning)

        return None

    def _get_metric_limit(self, instance=None):
        if instance is None:
            # NOTE: Agent 6+ will now always pass an instance when calling into a check, but we still need to
            # account for this case due to some tests not always passing an instance on init.
            self.log.debug(
                "No instance provided (this is deprecated!). Reverting to the default metric limit: %s",
                self.DEFAULT_METRIC_LIMIT,
            )
            return self.DEFAULT_METRIC_LIMIT

        max_returned_metrics = instance.get('max_returned_metrics', self.DEFAULT_METRIC_LIMIT)

        try:
            limit = int(max_returned_metrics)
        except (ValueError, TypeError):
            self.warning(
                "Configured 'max_returned_metrics' cannot be interpreted as an integer: %s. "
                "Reverting to the default limit: %s",
                max_returned_metrics,
                self.DEFAULT_METRIC_LIMIT,
            )
            return self.DEFAULT_METRIC_LIMIT

        # Do not allow to disable limiting if the class has set a non-zero default value.
        if limit == 0 and self.DEFAULT_METRIC_LIMIT > 0:
            self.warning(
                "Setting 'max_returned_metrics' to zero is not allowed. Reverting to the default metric limit: %s",
                self.DEFAULT_METRIC_LIMIT,
            )
            return self.DEFAULT_METRIC_LIMIT

        return limit

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
    def metadata_manager(self):
        if self._metadata_manager is None:
            if not self.check_id and not using_stub_aggregator:
                raise RuntimeError('Attribute `check_id` must be set')

            self._metadata_manager = MetadataManager(self.name, self.check_id, self.log, self.METADATA_TRANSFORMERS)

        return self._metadata_manager

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

    def _submit_metric(self, mtype, name, value, tags=None, hostname=None, device_name=None, raw=False):
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

        aggregator.submit_metric(self, self.check_id, mtype, self._format_namespace(name, raw), value, tags, hostname)

    def gauge(self, name, value, tags=None, hostname=None, device_name=None, raw=False):
        """Sample a gauge metric.

        :param str name: the name of the metric.
        :param float value: the value for the metric.
        :param list tags: (optional) a list of tags to associate with this metric.
        :param str hostname: (optional) a hostname to associate with this metric. Defaults to the current host.
        :param str device_name: **deprecated** add a tag in the form :code:`device:<device_name>` to the :code:`tags`
            list instead.
        :param bool raw: (optional) whether to ignore any defined namespace prefix
        """
        self._submit_metric(
            aggregator.GAUGE, name, value, tags=tags, hostname=hostname, device_name=device_name, raw=raw
        )

    def count(self, name, value, tags=None, hostname=None, device_name=None, raw=False):
        """Sample a raw count metric.

        :param str name: the name of the metric.
        :param float value: the value for the metric.
        :param list tags: (optional) a list of tags to associate with this metric.
        :param str hostname: (optional) a hostname to associate with this metric. Defaults to the current host.
        :param str device_name: **deprecated** add a tag in the form :code:`device:<device_name>` to the :code:`tags`
            list instead.
        :param bool raw: (optional) whether to ignore any defined namespace prefix
        """
        self._submit_metric(
            aggregator.COUNT, name, value, tags=tags, hostname=hostname, device_name=device_name, raw=raw
        )

    def monotonic_count(self, name, value, tags=None, hostname=None, device_name=None, raw=False):
        """Sample an increasing counter metric.

        :param str name: the name of the metric.
        :param float value: the value for the metric.
        :param list tags: (optional) a list of tags to associate with this metric.
        :param str hostname: (optional) a hostname to associate with this metric. Defaults to the current host.
        :param str device_name: **deprecated** add a tag in the form :code:`device:<device_name>` to the :code:`tags`
            list instead.
        :param bool raw: (optional) whether to ignore any defined namespace prefix
        """
        self._submit_metric(
            aggregator.MONOTONIC_COUNT, name, value, tags=tags, hostname=hostname, device_name=device_name, raw=raw
        )

    def rate(self, name, value, tags=None, hostname=None, device_name=None, raw=False):
        """Sample a point, with the rate calculated at the end of the check.

        :param str name: the name of the metric.
        :param float value: the value for the metric.
        :param list tags: (optional) a list of tags to associate with this metric.
        :param str hostname: (optional) a hostname to associate with this metric. Defaults to the current host.
        :param str device_name: **deprecated** add a tag in the form :code:`device:<device_name>` to the :code:`tags`
            list instead.
        :param bool raw: (optional) whether to ignore any defined namespace prefix
        """
        self._submit_metric(
            aggregator.RATE, name, value, tags=tags, hostname=hostname, device_name=device_name, raw=raw
        )

    def histogram(self, name, value, tags=None, hostname=None, device_name=None, raw=False):
        """Sample a histogram metric.

        :param str name: the name of the metric.
        :param float value: the value for the metric.
        :param list tags: (optional) a list of tags to associate with this metric.
        :param str hostname: (optional) a hostname to associate with this metric. Defaults to the current host.
        :param str device_name: **deprecated** add a tag in the form :code:`device:<device_name>` to the :code:`tags`
            list instead.
        :param bool raw: (optional) whether to ignore any defined namespace prefix
        """
        self._submit_metric(
            aggregator.HISTOGRAM, name, value, tags=tags, hostname=hostname, device_name=device_name, raw=raw
        )

    def historate(self, name, value, tags=None, hostname=None, device_name=None, raw=False):
        """Sample a histogram based on rate metrics.

        :param str name: the name of the metric.
        :param float value: the value for the metric.
        :param list tags: (optional) a list of tags to associate with this metric.
        :param str hostname: (optional) a hostname to associate with this metric. Defaults to the current host.
        :param str device_name: **deprecated** add a tag in the form :code:`device:<device_name>` to the :code:`tags`
            list instead.
        :param bool raw: (optional) whether to ignore any defined namespace prefix
        """
        self._submit_metric(
            aggregator.HISTORATE, name, value, tags=tags, hostname=hostname, device_name=device_name, raw=raw
        )

    def increment(self, name, value=1, tags=None, hostname=None, device_name=None, raw=False):
        """Increment a counter metric.

        :param str name: the name of the metric.
        :param float value: the value for the metric.
        :param list tags: (optional) a list of tags to associate with this metric.
        :param str hostname: (optional) a hostname to associate with this metric. Defaults to the current host.
        :param str device_name: **deprecated** add a tag in the form :code:`device:<device_name>` to the :code:`tags`
            list instead.
        :param bool raw: (optional) whether to ignore any defined namespace prefix
        """
        self._log_deprecation('increment')
        self._submit_metric(
            aggregator.COUNTER, name, value, tags=tags, hostname=hostname, device_name=device_name, raw=raw
        )

    def decrement(self, name, value=-1, tags=None, hostname=None, device_name=None, raw=False):
        """Decrement a counter metric.

        :param str name: the name of the metric.
        :param float value: the value for the metric.
        :param list tags: (optional) a list of tags to associate with this metric.
        :param str hostname: (optional) a hostname to associate with this metric. Defaults to the current host.
        :param str device_name: **deprecated** add a tag in the form :code:`device:<device_name>` to the :code:`tags`
            list instead.
        :param bool raw: (optional) whether to ignore any defined namespace prefix
        """
        self._log_deprecation('increment')
        self._submit_metric(
            aggregator.COUNTER, name, value, tags=tags, hostname=hostname, device_name=device_name, raw=raw
        )

    def service_check(self, name, status, tags=None, hostname=None, message=None, raw=False):
        """Send the status of a service.

        :param str name: the name of the service check.
        :param status: a constant describing the service status.
        :type status: :py:class:`datadog_checks.base.constants.ServiceCheck`
        :param list tags: (optional) a list of tags to associate with this check.
        :param str message: (optional) additional information or a description of why this status occurred.
        :param bool raw: (optional) whether to ignore any defined namespace prefix
        """
        tags = self._normalize_tags_type(tags)
        if hostname is None:
            hostname = ''
        if message is None:
            message = ''
        else:
            message = to_string(message)

        aggregator.submit_service_check(
            self, self.check_id, self._format_namespace(name, raw), status, tags, hostname, message
        )

    def _log_deprecation(self, deprecation_key, *args):
        """
        Logs a deprecation notice at most once per AgentCheck instance, for the pre-defined `deprecation_key`
        """
        if not self._deprecations[deprecation_key][0]:
            self.warning(self._deprecations[deprecation_key][1], *args)
            self._deprecations[deprecation_key][0] = True

    # TODO: Remove once our checks stop calling it
    def service_metadata(self, meta_name, value):
        pass

    def set_metadata(self, name, value, **options):
        """Updates the cached metadata ``name`` with ``value``, which is then sent by the Agent at regular intervals.

        :param str name: the name of the metadata
        :param object value: the value for the metadata. if ``name`` has no transformer defined then the
                             raw ``value`` will be submitted and therefore it must be a ``str``
        :param options: keyword arguments to pass to any defined transformer
        """
        self.metadata_manager.submit(name, value, options)

    def send_config_metadata(self):
        self.set_metadata('config', self.instance, section='instance', whitelist=self.METADATA_DEFAULT_CONFIG_INSTANCE)
        self.set_metadata(
            'config', self.init_config, section='init_config', whitelist=self.METADATA_DEFAULT_CONFIG_INIT_CONFIG
        )

    @staticmethod
    def is_metadata_collection_enabled():
        return is_affirmative(datadog_agent.get_config('enable_metadata_collection'))

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
            self.log.exception('Unexpected external tags format: %s', external_tags)
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

    def warning(self, warning_message, *args, **kwargs):
        """Log a warning message and display it in the Agent's status page.

        Using *args is intended to make warning work like log.warn/debug/info/etc
        and make it compliant with flake8 logging format linter.

        :param str warning_message: the warning message.
        :param list args: format string args used to format warning_message e.g. `warning_message % args`
        :param dict kwargs: not used for now, but added to match Python logger's `warning` method signature
        """
        warning_message = to_string(warning_message)
        # Interpolate message only if args is not empty. Same behavior as python logger:
        # https://github.com/python/cpython/blob/1dbe5373851acb85ba91f0be7b83c69563acd68d/Lib/logging/__init__.py#L368-L369
        if args:
            warning_message = warning_message % args
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

    def _format_namespace(self, s, raw=False):
        if not raw and self.__NAMESPACE__:
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
            name = self.METRIC_REPLACEMENT.sub(br'_', metric)
            name = self.DOT_UNDERSCORE_CLEANUP.sub(br'.', name).strip(b'_')

        name = self.MULTIPLE_UNDERSCORE_CLEANUP.sub(br'_', name)

        if prefix is not None:
            name = ensure_bytes(prefix) + b"." + name

        return to_string(name)

    def normalize_tag(self, tag):
        """Normalize tag values.

        This happens for legacy reasons, when we cleaned up some characters (like '-')
        which are allowed in tags.
        """
        if isinstance(tag, text_type):
            tag = tag.encode('utf-8', 'ignore')
        tag = self.TAG_REPLACEMENT.sub(br'_', tag)
        tag = self.MULTIPLE_UNDERSCORE_CLEANUP.sub(br'_', tag)
        tag = self.DOT_UNDERSCORE_CLEANUP.sub(br'.', tag).strip(b'_')
        return to_string(tag)

    def check(self, instance):
        raise NotImplementedError

    def run(self):
        try:
            while self.check_initializations:
                initialization = self.check_initializations.popleft()
                try:
                    initialization()
                except Exception:
                    self.check_initializations.appendleft(initialization)
                    raise

            instance = copy.deepcopy(self.instances[0])

            if 'set_breakpoint' in self.init_config:
                from ..utils.agent.debug import enter_pdb

                enter_pdb(self.check, line=self.init_config['set_breakpoint'], args=(instance,))
            elif 'profile_memory' in self.init_config or (
                datadog_agent.tracemalloc_enabled() and should_profile_memory(datadog_agent, self.name)
            ):
                from ..utils.agent.memory import profile_memory

                metrics = profile_memory(
                    self.check, self.init_config, namespaces=self.check_id.split(':', 1), args=(instance,)
                )

                tags = ['check_name:{}'.format(self.name), 'check_version:{}'.format(self.check_version)]
                tags.extend(instance.get('__memory_profiling_tags', []))
                for m in metrics:
                    self.gauge(m.name, m.value, tags=tags, raw=True)
            else:
                self.check(instance)

            result = ''
        except Exception as e:
            result = json.dumps([{'message': str(e), 'traceback': traceback.format_exc()}])
        finally:
            if self.metric_limiter:
                self.metric_limiter.reset()

        return result

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
        for key, value in iteritems(event):
            if not isinstance(value, text_type):
                continue
            try:
                event[key] = to_string(event[key])
            except UnicodeError:
                self.log.warning('Encoding error with field `%s`, cannot submit event', key)
                return

        if event.get('tags'):
            event['tags'] = self._normalize_tags_type(event['tags'])
        if event.get('timestamp'):
            event['timestamp'] = int(event['timestamp'])
        if event.get('aggregation_key'):
            event['aggregation_key'] = to_string(event['aggregation_key'])

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
            try:
                normalized_tags.append('device:{}'.format(to_string(device_name)))
            except UnicodeError:
                self.log.warning(
                    'Encoding error with device name `%r` for metric `%r`, ignoring tag', device_name, metric_name
                )
        if tags is not None:
            for tag in tags:
                if tag is None:
                    continue
                try:
                    tag = to_string(tag)
                except UnicodeError:
                    self.log.warning('Encoding error with tag `%s` for metric `%s`, ignoring tag', tag, metric_name)
                    continue

                normalized_tags.append(tag)

        return normalized_tags
