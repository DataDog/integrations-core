# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import copy
import functools
import importlib
import logging
import os
import re
from collections import deque
from os.path import basename
from typing import (  # noqa: F401
    TYPE_CHECKING,
    Any,
    AnyStr,
    Callable,
    Deque,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

import lazy_loader

from datadog_checks.base.agent import AGENT_RUNNING, aggregator, datadog_agent
from datadog_checks.base.config import is_affirmative
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.base.errors import ConfigurationError
from datadog_checks.base.utils.agent.utils import should_profile_memory
from datadog_checks.base.utils.common import ensure_bytes, to_native_string
from datadog_checks.base.utils.fips import enable_fips
from datadog_checks.base.utils.format import json
from datadog_checks.base.utils.tagging import GENERIC_TAGS
from datadog_checks.base.utils.tracing import traced_class

from ._config_ast import parse as _parse_ast_config

if AGENT_RUNNING:
    from datadog_checks.base.log import CheckLoggingAdapter, init_logging

else:
    from datadog_checks.base.stubs.log import CheckLoggingAdapter, init_logging

init_logging()

if datadog_agent.get_config('integration_tracing'):
    from ddtrace import patch

    # handle thread monitoring as an additional option
    # See: http://pypi.datadoghq.com/trace/docs/other_integrations.html#futures
    if datadog_agent.get_config('integration_tracing_futures'):
        patch(logging=True, requests=True, futures=True)
    else:
        patch(logging=True, requests=True)

if is_affirmative(datadog_agent.get_config('integration_profiling')):
    from ddtrace.profiling import Profiler

    prof = Profiler(service='datadog-agent-integrations')
    prof.start()

if TYPE_CHECKING:
    import inspect as _module_inspect
    import ssl  # noqa: F401
    import traceback as _module_traceback
    import unicodedata as _module_unicodedata

    from datadog_checks.base.utils.diagnose import Diagnosis
    from datadog_checks.base.utils.http import RequestsWrapper
    from datadog_checks.base.utils.metadata import MetadataManager

inspect: _module_inspect = lazy_loader.load('inspect')
traceback: _module_traceback = lazy_loader.load('traceback')
unicodedata: _module_unicodedata = lazy_loader.load('unicodedata')

# Metric types for which it's only useful to submit once per set of tags
ONE_PER_CONTEXT_METRIC_TYPES = [aggregator.GAUGE, aggregator.RATE, aggregator.MONOTONIC_COUNT]
TYPO_SIMILARITY_THRESHOLD = 0.95


@traced_class
class AgentCheck(object):
    """
    The base class for any Agent based integration.

    In general, you don't need to and you should not override anything from the base
    class except the `check` method but sometimes it might be useful for a Check to
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

    !!! note
        when loading a Custom check, the Agent will inspect the module searching
        for a subclass of `AgentCheck`. If such a class exists but has been derived in
        turn, it'll be ignored - **you should never derive from an existing Check**.
    """

    # If defined, this will be the prefix of every metric/service check and the source type of events
    __NAMESPACE__ = ''

    OK, WARNING, CRITICAL, UNKNOWN = ServiceCheck

    # Used by `self.http` for an instance of RequestsWrapper
    HTTP_CONFIG_REMAPPER = None

    # Used by `create_tls_context` for an instance of RequestsWrapper
    TLS_CONFIG_REMAPPER = None

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

    FIRST_CAP_RE = re.compile(rb'(.)([A-Z][a-z]+)')
    ALL_CAP_RE = re.compile(rb'([a-z0-9])([A-Z])')
    METRIC_REPLACEMENT = re.compile(rb'([^a-zA-Z0-9_.]+)|(^[^a-zA-Z]+)')
    TAG_REPLACEMENT = re.compile(rb'[,\+\*\-/()\[\]{}\s]')
    MULTIPLE_UNDERSCORE_CLEANUP = re.compile(rb'__+')
    DOT_UNDERSCORE_CLEANUP = re.compile(rb'_*\._*')

    # allows to set a limit on the number of metric name and tags combination
    # this check can send per run. This is useful for checks that have an unbounded
    # number of tag values that depend on the input payload.
    # The logic counts one set of tags per gauge/rate/monotonic_count call, and de-duplicates
    # sets of tags for other metric types. The first N sets of tags in submission order will
    # be sent to the aggregator, the rest are dropped. The state is reset after each run.
    # See https://github.com/DataDog/integrations-core/pull/2093 for more information.
    DEFAULT_METRIC_LIMIT = 0

    # Allow tracing for classic integrations
    def __init_subclass__(cls, *args, **kwargs):
        try:
            # https://github.com/python/mypy/issues/4660
            super().__init_subclass__(*args, **kwargs)  # type: ignore
            return traced_class(cls)
        except Exception:
            return cls

    def __init__(self, *args, **kwargs):
        # type: (*Any, **Any) -> None
        """
        Parameters:
            name (str):
                the name of the check
            init_config (dict):
                the `init_config` section of the configuration.
            instance (list[dict]):
                a one-element list containing the instance options from the
                configuration file (a list is used to keep backward compatibility with
                older versions of the Agent).
        """
        # NOTE: these variable assignments exist to ease type checking when eventually assigned as attributes.
        name = kwargs.get('name', '')
        init_config = kwargs.get('init_config', {})
        agentConfig = kwargs.get('agentConfig', {})
        instances = kwargs.get('instances', [])

        if len(args) > 0:
            name = args[0]
        if len(args) > 1:
            init_config = args[1]
        if len(args) > 2:
            # agent pass instances as tuple but in test we are usually using list, so we are testing for both
            if len(args) > 3 or not isinstance(args[2], (list, tuple)) or 'instances' in kwargs:
                # old-style init: the 3rd argument is `agentConfig`
                agentConfig = args[2]
                if len(args) > 3:
                    instances = args[3]
            else:
                # new-style init: the 3rd argument is `instances`
                instances = args[2]

        # NOTE: Agent 6+ should pass exactly one instance... But we are not abiding by that rule on our side
        # everywhere just yet. It's complicated... See: https://github.com/DataDog/integrations-core/pull/5573
        instance = instances[0] if instances else None

        self.check_id = ''
        self.name = name  # type: str
        self.init_config = init_config  # type: InitConfigType
        self.agentConfig = agentConfig  # type: AgentConfigType
        self.instance = instance  # type: InstanceType
        self.instances = instances  # type: List[InstanceType]
        self.warnings = []  # type: List[str]
        self.disable_generic_tags = (
            is_affirmative(self.instance.get('disable_generic_tags', False)) if instance else False
        )
        self.debug_metrics = {}
        if self.init_config is not None:
            self.debug_metrics.update(self.init_config.get('debug_metrics', {}))
        if self.instance is not None:
            self.debug_metrics.update(self.instance.get('debug_metrics', {}))

        # `self.hostname` is deprecated, use `datadog_agent.get_hostname()` instead
        self.hostname = datadog_agent.get_hostname()  # type: str

        logger = logging.getLogger('{}.{}'.format(__name__, self.name))
        self.log = CheckLoggingAdapter(logger, self)

        metric_patterns = self.instance.get('metric_patterns', {}) if instance else {}
        if not isinstance(metric_patterns, dict):
            raise ConfigurationError('Setting `metric_patterns` must be a mapping')

        self.exclude_metrics_pattern = self._create_metrics_pattern(metric_patterns, 'exclude')
        self.include_metrics_pattern = self._create_metrics_pattern(metric_patterns, 'include')

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
            'increment': (
                False,
                (
                    'DEPRECATION NOTICE: `AgentCheck.increment`/`AgentCheck.decrement` are deprecated, please '
                    'use `AgentCheck.gauge` or `AgentCheck.count` instead, with a different metric name'
                ),
            ),
            'device_name': (
                False,
                (
                    'DEPRECATION NOTICE: `device_name` is deprecated, please use a `device:` '
                    'tag in the `tags` list instead'
                ),
            ),
            'in_developer_mode': (
                False,
                'DEPRECATION NOTICE: `in_developer_mode` is deprecated, please stop using it.',
            ),
            'no_proxy': (
                False,
                (
                    'DEPRECATION NOTICE: The `no_proxy` config option has been renamed '
                    'to `skip_proxy` and will be removed in a future release.'
                ),
            ),
            'service_tag': (
                False,
                (
                    'DEPRECATION NOTICE: The `service` tag is deprecated and has been renamed to `%s`. '
                    'Set `disable_legacy_service_tag` to `true` to disable this warning. '
                    'The default will become `true` and cannot be changed in Agent version 8.'
                ),
            ),
            '_config_renamed': (
                False,
                (
                    'DEPRECATION NOTICE: The `%s` config option has been renamed '
                    'to `%s` and will be removed in a future release.'
                ),
            ),
        }  # type: Dict[str, Tuple[bool, str]]

        # Setup metric limits
        self.metric_limiter = self._get_metric_limiter(self.name, instance=self.instance)

        # Lazily load and validate config
        self._config_model_instance = None  # type: Any
        self._config_model_shared = None  # type: Any

        # Functions that will be called exactly once (if successful) before the first check run
        self.check_initializations = deque()  # type: Deque[Callable[[], None]]

        self.check_initializations.append(self.load_configuration_models)

        self.__formatted_tags = None
        self.__logs_enabled = None

        if os.environ.get("GOFIPS", "0") == "1":
            enable_fips()

    def _create_metrics_pattern(self, metric_patterns, option_name):
        all_patterns = metric_patterns.get(option_name, [])

        if not isinstance(all_patterns, list):
            raise ConfigurationError('Setting `{}` of `metric_patterns` must be an array'.format(option_name))

        metrics_patterns = []
        for i, entry in enumerate(all_patterns, 1):
            if not isinstance(entry, str):
                raise ConfigurationError(
                    'Entry #{} of setting `{}` of `metric_patterns` must be a string'.format(i, option_name)
                )
            if not entry:
                self.log.debug(
                    'Entry #%s of setting `%s` of `metric_patterns` must not be empty, ignoring', i, option_name
                )
                continue

            metrics_patterns.append(entry)

        if metrics_patterns:
            return re.compile('|'.join(metrics_patterns))

        return None

    def _get_metric_limiter(self, name, instance=None):
        # type: (str, InstanceType) -> Optional[Limiter]
        limit = self._get_metric_limit(instance=instance)

        if limit > 0:
            # See Performance Optimizations in this package's README.md.
            from datadog_checks.base.utils.limiter import Limiter

            return Limiter(name, 'metrics', limit, self.warning)

        return None

    def _get_metric_limit(self, instance=None):
        # type: (InstanceType) -> int
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

    @property
    def http(self) -> RequestsWrapper:
        """
        Provides logic to yield consistent network behavior based on user configuration.

        Only new checks or checks on Agent 6.13+ can and should use this for HTTP requests.
        """
        if not hasattr(self, '_http'):
            # See Performance Optimizations in this package's README.md.
            from datadog_checks.base.utils.http import RequestsWrapper

            self._http = RequestsWrapper(self.instance or {}, self.init_config, self.HTTP_CONFIG_REMAPPER, self.log)

        return self._http

    @property
    def logs_enabled(self):
        # type: () -> bool
        """
        Returns True if logs are enabled, False otherwise.
        """
        if self.__logs_enabled is None:
            self.__logs_enabled = bool(datadog_agent.get_config('logs_enabled'))

        return self.__logs_enabled

    @property
    def formatted_tags(self):
        # type: () -> str
        if self.__formatted_tags is None:
            normalized_tags = set()
            for tag in self.instance.get('tags', []):
                key, _, value = tag.partition(':')
                if not value:
                    continue

                if self.disable_generic_tags and key in GENERIC_TAGS:
                    key = '{}_{}'.format(self.name, key)

                normalized_tags.add('{}:{}'.format(key, value))

            self.__formatted_tags = ','.join(sorted(normalized_tags))

        return self.__formatted_tags

    @property
    def diagnosis(self) -> Diagnosis:
        """
        A Diagnosis object to register explicit diagnostics and record diagnoses.
        """
        if not hasattr(self, '_diagnosis'):
            # See Performance Optimizations in this package's README.md.
            from datadog_checks.base.utils.diagnose import Diagnosis

            self._diagnosis = Diagnosis(sanitize=self.sanitize)
        return self._diagnosis

    def get_tls_context(self, refresh=False, overrides=None):
        # type: (bool, Dict[AnyStr, Any]) -> ssl.SSLContext
        """
        Creates and cache an SSLContext instance based on user configuration.
        Note that user configuration can be overridden by using `overrides`.
        This should only be applied to older integration that manually set config values.

        Since: Agent 7.24
        """
        if not hasattr(self, '_tls_context_wrapper'):
            # See Performance Optimizations in this package's README.md.
            from datadog_checks.base.utils.tls import TlsContextWrapper

            self._tls_context_wrapper = TlsContextWrapper(
                self.instance or {}, self.TLS_CONFIG_REMAPPER, overrides=overrides
            )

        if refresh:
            self._tls_context_wrapper.refresh_tls_context()

        return self._tls_context_wrapper.tls_context

    @property
    def metadata_manager(self) -> MetadataManager:
        """
        Used for sending metadata via Go bindings.
        """
        if not hasattr(self, '_metadata_manager'):
            if not self.check_id and AGENT_RUNNING:
                raise RuntimeError('Attribute `check_id` must be set')

            # See Performance Optimizations in this package's README.md.
            from datadog_checks.base.utils.metadata import MetadataManager

            self._metadata_manager = MetadataManager(self.name, self.check_id, self.log, self.METADATA_TRANSFORMERS)

        return self._metadata_manager

    @property
    def check_version(self):
        # type: () -> str
        """
        Return the dynamically detected integration version.
        """
        if not hasattr(self, '_check_version'):
            # 'datadog_checks.<PACKAGE>.<MODULE>...'
            module_parts = self.__module__.split('.')
            package_path = '.'.join(module_parts[:2])
            package = importlib.import_module(package_path)

            # Provide a default just in case
            self._check_version = getattr(package, '__version__', '0.0.0')

        return self._check_version

    @property
    def in_developer_mode(self):
        # type: () -> bool
        self._log_deprecation('in_developer_mode')
        return False

    def log_typos_in_options(self, user_config, models_config, level):
        # See Performance Optimizations in this package's README.md.
        from jellyfish import jaro_winkler_similarity
        from pydantic import BaseModel

        user_configs = user_config or {}  # type: Dict[str, Any]
        models_config = models_config or {}
        typos = set()  # type: Set[str]

        known_options = {k for k, _ in models_config}  # type: Set[str]

        if isinstance(models_config, BaseModel):
            # Also add aliases, if any
            known_options.update(set(models_config.model_dump(by_alias=True)))

        unknown_options = [option for option in user_configs.keys() if option not in known_options]  # type: List[str]

        for unknown_option in unknown_options:
            similar_known_options = []  # type: List[Tuple[str, int]]
            for known_option in known_options:
                ratio = jaro_winkler_similarity(unknown_option, known_option)
                if ratio > TYPO_SIMILARITY_THRESHOLD:
                    similar_known_options.append((known_option, ratio))
                    typos.add(unknown_option)

            if len(similar_known_options) > 0:
                similar_known_options.sort(key=lambda option: option[1], reverse=True)
                similar_known_options_names = [option[0] for option in similar_known_options]  # type: List[str]
                message = (
                    'Detected potential typo in configuration option in {}/{} section: `{}`. Did you mean {}?'
                ).format(self.name, level, unknown_option, ', or '.join(similar_known_options_names))
                self.log.warning(message)
        return typos

    def load_configuration_models(self, package_path=None):
        if package_path is None:
            # 'datadog_checks.<PACKAGE>.<MODULE>...'
            module_parts = self.__module__.split('.')
            package_path = '{}.config_models'.format('.'.join(module_parts[:2]))
        if self._config_model_shared is None:
            shared_config = copy.deepcopy(self.init_config)
            context = self._get_config_model_context(shared_config)
            shared_model = self.load_configuration_model(package_path, 'SharedConfig', shared_config, context)
            try:
                self.log_typos_in_options(shared_config, shared_model, 'init_config')
            except Exception as e:
                self.log.debug("Failed to detect typos in `init_config` section: %s", e)
            if shared_model is not None:
                self._config_model_shared = shared_model

        if self._config_model_instance is None:
            instance_config = copy.deepcopy(self.instance)
            context = self._get_config_model_context(instance_config)
            instance_model = self.load_configuration_model(package_path, 'InstanceConfig', instance_config, context)
            try:
                self.log_typos_in_options(instance_config, instance_model, 'instances')
            except Exception as e:
                self.log.debug("Failed to detect typos in `instances` section: %s", e)
            if instance_model is not None:
                self._config_model_instance = instance_model

    @staticmethod
    def load_configuration_model(import_path, model_name, config, context):
        try:
            package = importlib.import_module(import_path)
        except ModuleNotFoundError as e:
            # Don't fail if there are no models
            if str(e).startswith('No module named '):
                return

            raise

        model = getattr(package, model_name, None)
        if model is not None:
            from pydantic import ValidationError

            try:
                config_model = model.model_validate(config, context=context)
            except ValidationError as e:
                errors = e.errors()
                num_errors = len(errors)
                message_lines = [
                    'Detected {} error{} while loading configuration model `{}`:'.format(
                        num_errors, 's' if num_errors > 1 else '', model_name
                    )
                ]

                for error in errors:
                    message_lines.append(
                        ' -> '.join(
                            # Start array indexes at one for user-friendliness
                            str(loc + 1) if isinstance(loc, int) else str(loc)
                            for loc in error['loc']
                        )
                    )
                    message_lines.append('  {}'.format(error['msg']))

                raise ConfigurationError('\n'.join(message_lines)) from None
            else:
                return config_model

    def _get_config_model_context(self, config):
        return {'logger': self.log, 'warning': self.warning, 'configured_fields': frozenset(config)}

    def register_secret(self, secret: str) -> None:
        """
        Register a secret to be scrubbed by `.sanitize()`.
        """
        if not hasattr(self, '_sanitizer'):
            # See Performance Optimizations in this package's README.md.
            from datadog_checks.base.utils.secrets import SecretsSanitizer

            # Configure lazily so that checks that don't use sanitization aren't affected.
            self._sanitizer = SecretsSanitizer()
            self.log.setup_sanitization(sanitize=self.sanitize)

        self._sanitizer.register(secret)

    def sanitize(self, text):
        # type: (str) -> str
        """
        Scrub any registered secrets in `text`.
        """
        try:
            sanitizer = self._sanitizer
        except AttributeError:
            return text
        else:
            return sanitizer.sanitize(text)

    def _context_uid(self, mtype, name, tags=None, hostname=None):
        # type: (int, str, Sequence[str], str) -> str
        return '{}-{}-{}-{}'.format(mtype, name, tags if tags is None else hash(frozenset(tags)), hostname)

    def submit_histogram_bucket(
        self, name, value, lower_bound, upper_bound, monotonic, hostname, tags, raw=False, flush_first_value=False
    ):
        # type: (str, float, int, int, bool, str, Sequence[str], bool, bool) -> None
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
            if not AGENT_RUNNING:
                raise ValueError(err_msg)
            self.warning(err_msg)
            return

        tags = self._normalize_tags_type(tags, metric_name=name)
        if hostname is None:
            hostname = ''

        aggregator.submit_histogram_bucket(
            self,
            self.check_id,
            self._format_namespace(name, raw),
            value,
            lower_bound,
            upper_bound,
            monotonic,
            hostname,
            tags,
            flush_first_value,
        )

    def database_monitoring_query_sample(self, raw_event):
        # type: (str) -> None
        if raw_event is None:
            return

        aggregator.submit_event_platform_event(self, self.check_id, to_native_string(raw_event), "dbm-samples")

    def database_monitoring_query_metrics(self, raw_event):
        # type: (str) -> None
        if raw_event is None:
            return

        aggregator.submit_event_platform_event(self, self.check_id, to_native_string(raw_event), "dbm-metrics")

    def database_monitoring_query_activity(self, raw_event):
        # type: (str) -> None
        if raw_event is None:
            return

        aggregator.submit_event_platform_event(self, self.check_id, to_native_string(raw_event), "dbm-activity")

    def database_monitoring_metadata(self, raw_event):
        # type: (str) -> None
        if raw_event is None:
            return

        aggregator.submit_event_platform_event(self, self.check_id, to_native_string(raw_event), "dbm-metadata")

    def event_platform_event(self, raw_event, event_track_type):
        # type: (str, str) -> None
        """Send an event platform event.

        Parameters:
            raw_event (str):
                JSON formatted string representing the event to send
            event_track_type (str):
                type of event ingested and processed by the event platform
        """
        if raw_event is None:
            return
        aggregator.submit_event_platform_event(self, self.check_id, to_native_string(raw_event), event_track_type)

    def should_send_metric(self, metric_name):
        return not self._metric_excluded(metric_name) and self._metric_included(metric_name)

    def _metric_included(self, metric_name):
        if self.include_metrics_pattern is None:
            return True

        return self.include_metrics_pattern.search(metric_name) is not None

    def _metric_excluded(self, metric_name):
        if self.exclude_metrics_pattern is None:
            return False

        return self.exclude_metrics_pattern.search(metric_name) is not None

    def _submit_metric(
        self, mtype, name, value, tags=None, hostname=None, device_name=None, raw=False, flush_first_value=False
    ):
        # type: (int, str, float, Sequence[str], str, str, bool, bool) -> None
        if value is None:
            # ignore metric sample
            return

        name = self._format_namespace(name, raw)
        if not self.should_send_metric(name):
            return

        tags = self._normalize_tags_type(tags or [], device_name, name)
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
            if not AGENT_RUNNING:
                raise ValueError(err_msg)
            self.warning(err_msg)
            return

        aggregator.submit_metric(self, self.check_id, mtype, name, value, tags, hostname, flush_first_value)

    def gauge(self, name, value, tags=None, hostname=None, device_name=None, raw=False):
        # type: (str, float, Sequence[str], str, str, bool) -> None
        """Sample a gauge metric.

        Parameters:
            name (str):
                the name of the metric
            value (float):
                the value for the metric
            tags (list[str]):
                a list of tags to associate with this metric
            hostname (str):
                a hostname to associate with this metric. Defaults to the current host.
            device_name (str):
                **deprecated** add a tag in the form `device:<device_name>` to the `tags` list instead.
            raw (bool):
                whether to ignore any defined namespace prefix
        """
        self._submit_metric(
            aggregator.GAUGE, name, value, tags=tags, hostname=hostname, device_name=device_name, raw=raw
        )

    def count(self, name, value, tags=None, hostname=None, device_name=None, raw=False):
        # type: (str, float, Sequence[str], str, str, bool) -> None
        """Sample a raw count metric.

        Parameters:
            name (str):
                the name of the metric
            value (float):
                the value for the metric
            tags (list[str]):
                a list of tags to associate with this metric
            hostname (str):
                a hostname to associate with this metric. Defaults to the current host.
            device_name (str):
                **deprecated** add a tag in the form `device:<device_name>` to the `tags` list instead.
            raw (bool):
                whether to ignore any defined namespace prefix
        """
        self._submit_metric(
            aggregator.COUNT, name, value, tags=tags, hostname=hostname, device_name=device_name, raw=raw
        )

    def monotonic_count(
        self, name, value, tags=None, hostname=None, device_name=None, raw=False, flush_first_value=False
    ):
        # type: (str, float, Sequence[str], str, str, bool, bool) -> None
        """Sample an increasing counter metric.

        Parameters:
            name (str):
                the name of the metric
            value (float):
                the value for the metric
            tags (list[str]):
                a list of tags to associate with this metric
            hostname (str):
                a hostname to associate with this metric. Defaults to the current host.
            device_name (str):
                **deprecated** add a tag in the form `device:<device_name>` to the `tags` list instead.
            raw (bool):
                whether to ignore any defined namespace prefix
            flush_first_value (bool):
                whether to sample the first value
        """
        self._submit_metric(
            aggregator.MONOTONIC_COUNT,
            name,
            value,
            tags=tags,
            hostname=hostname,
            device_name=device_name,
            raw=raw,
            flush_first_value=flush_first_value,
        )

    def rate(self, name, value, tags=None, hostname=None, device_name=None, raw=False):
        # type: (str, float, Sequence[str], str, str, bool) -> None
        """Sample a point, with the rate calculated at the end of the check.

        Parameters:
            name (str):
                the name of the metric
            value (float):
                the value for the metric
            tags (list[str]):
                a list of tags to associate with this metric
            hostname (str):
                a hostname to associate with this metric. Defaults to the current host.
            device_name (str):
                **deprecated** add a tag in the form `device:<device_name>` to the `tags` list instead.
            raw (bool):
                whether to ignore any defined namespace prefix
        """
        self._submit_metric(
            aggregator.RATE, name, value, tags=tags, hostname=hostname, device_name=device_name, raw=raw
        )

    def histogram(self, name, value, tags=None, hostname=None, device_name=None, raw=False):
        # type: (str, float, Sequence[str], str, str, bool) -> None
        """Sample a histogram metric.

        Parameters:
            name (str):
                the name of the metric
            value (float):
                the value for the metric
            tags (list[str]):
                a list of tags to associate with this metric
            hostname (str):
                a hostname to associate with this metric. Defaults to the current host.
            device_name (str):
                **deprecated** add a tag in the form `device:<device_name>` to the `tags` list instead.
            raw (bool):
                whether to ignore any defined namespace prefix
        """
        self._submit_metric(
            aggregator.HISTOGRAM, name, value, tags=tags, hostname=hostname, device_name=device_name, raw=raw
        )

    def historate(self, name, value, tags=None, hostname=None, device_name=None, raw=False):
        # type: (str, float, Sequence[str], str, str, bool) -> None
        """Sample a histogram based on rate metrics.

        Parameters:
            name (str):
                the name of the metric
            value (float):
                the value for the metric
            tags (list[str]):
                a list of tags to associate with this metric
            hostname (str):
                a hostname to associate with this metric. Defaults to the current host.
            device_name (str):
                **deprecated** add a tag in the form `device:<device_name>` to the `tags` list instead.
            raw (bool):
                whether to ignore any defined namespace prefix
        """
        self._submit_metric(
            aggregator.HISTORATE, name, value, tags=tags, hostname=hostname, device_name=device_name, raw=raw
        )

    def increment(self, name, value=1, tags=None, hostname=None, device_name=None, raw=False):
        # type: (str, float, Sequence[str], str, str, bool) -> None
        """Increment a counter metric.

        Parameters:
            name (str):
                the name of the metric
            value (float):
                the value for the metric
            tags (list[str]):
                a list of tags to associate with this metric
            hostname (str):
                a hostname to associate with this metric. Defaults to the current host.
            device_name (str):
                **deprecated** add a tag in the form `device:<device_name>` to the `tags` list instead.
            raw (bool):
                whether to ignore any defined namespace prefix
        """
        self._log_deprecation('increment')
        self._submit_metric(
            aggregator.COUNTER, name, value, tags=tags, hostname=hostname, device_name=device_name, raw=raw
        )

    def decrement(self, name, value=-1, tags=None, hostname=None, device_name=None, raw=False):
        # type: (str, float, Sequence[str], str, str, bool) -> None
        """Decrement a counter metric.

        Parameters:
            name (str):
                the name of the metric
            value (float):
                the value for the metric
            tags (list[str]):
                a list of tags to associate with this metric
            hostname (str):
                a hostname to associate with this metric. Defaults to the current host.
            device_name (str):
                **deprecated** add a tag in the form `device:<device_name>` to the `tags` list instead.
            raw (bool):
                whether to ignore any defined namespace prefix
        """
        self._log_deprecation('increment')
        self._submit_metric(
            aggregator.COUNTER, name, value, tags=tags, hostname=hostname, device_name=device_name, raw=raw
        )

    def service_check(self, name, status, tags=None, hostname=None, message=None, raw=False):
        # type: (str, ServiceCheckStatus, Sequence[str], str, str, bool) -> None
        """Send the status of a service.

        !!! warning "Soft Deprecation"
            When building new checks avoid submitting service checks.
            **Checks that already submit service checks will continue to do so.**

        Parameters:
            name (str):
                the name of the service check
            status (int):
                a constant describing the service status
            tags (list[str]):
                a list of tags to associate with this service check
            message (str):
                additional information or a description of why this status occurred.
            raw (bool):
                whether to ignore any defined namespace prefix
        """
        tags = self._normalize_tags_type(tags or [])
        if hostname is None:
            hostname = ''
        if message is None:
            message = ''
        else:
            message = to_native_string(message)

        message = self.sanitize(message)

        aggregator.submit_service_check(
            self, self.check_id, self._format_namespace(name, raw), status, tags, hostname, message
        )

    def send_log(self, data, cursor=None, stream='default'):
        # type: (dict[str, str], dict[str, Any] | None, str) -> None
        """Send a log for submission.

        Parameters:
            data (dict[str, str]):
                The log data to send. The following keys are treated specially, if present:

                - timestamp: should be an integer or float representing the number of seconds since the Unix epoch
                - ddtags: if not defined, it will automatically be set based on the instance's `tags` option
            cursor (dict[str, Any] or None):
                Metadata associated with the log which will be saved to disk. The most recent value may be
                retrieved with the `get_log_cursor` method.
            stream (str):
                The stream associated with this log, used for accurate cursor persistence.
                Has no effect if `cursor` argument is `None`.
        """
        attributes = data.copy()
        if 'ddtags' not in attributes and self.formatted_tags:
            attributes['ddtags'] = self.formatted_tags

        timestamp = attributes.get('timestamp')
        if timestamp is not None:
            # convert seconds to milliseconds
            attributes['timestamp'] = int(timestamp * 1000)

        datadog_agent.send_log(json.encode(attributes), self.check_id)
        if cursor is not None:
            self.write_persistent_cache('log_cursor_{}'.format(stream), json.encode(cursor))

    def get_log_cursor(self, stream='default'):
        # type: (str) -> dict[str, Any] | None
        """Returns the most recent log cursor from disk."""
        data = self.read_persistent_cache('log_cursor_{}'.format(stream))
        return json.decode(data) if data else None

    def _log_deprecation(self, deprecation_key, *args):
        # type: (str, *str) -> None
        """
        Logs a deprecation notice at most once per AgentCheck instance, for the pre-defined `deprecation_key`
        """
        sent, message = self._deprecations[deprecation_key]
        if sent:
            return

        self.warning(message, *args)
        self._deprecations[deprecation_key] = (True, message)

    # TODO: Remove once our checks stop calling it
    def service_metadata(self, meta_name, value):
        # type: (str, Any) -> None
        pass

    def set_metadata(self, name, value, **options):
        # type: (str, Any, **Any) -> None
        """Updates the cached metadata `name` with `value`, which is then sent by the Agent at regular intervals.

        Parameters:
            name (str):
                the name of the metadata
            value (Any):
                the value for the metadata. if ``name`` has no transformer defined then the
                raw ``value`` will be submitted and therefore it must be a ``str``
            options (Any):
                keyword arguments to pass to any defined transformer
        """
        self.metadata_manager.submit(name, value, options)

    @staticmethod
    def is_metadata_collection_enabled():
        # type: () -> bool
        return is_affirmative(datadog_agent.get_config('enable_metadata_collection'))

    @classmethod
    def metadata_entrypoint(cls, method):
        # type: (Callable[..., None]) -> Callable[..., None]
        """
        Skip execution of the decorated method if metadata collection is disabled on the Agent.

        Usage:

        ```python
        class MyCheck(AgentCheck):
            @AgentCheck.metadata_entrypoint
            def collect_metadata(self):
                ...
        ```
        """

        @functools.wraps(method)
        def entrypoint(self, *args, **kwargs):
            # type: (AgentCheck, *Any, **Any) -> None
            if not self.is_metadata_collection_enabled():
                return

            # NOTE: error handling still at the discretion of the wrapped method.
            method(self, *args, **kwargs)

        return entrypoint

    def _persistent_cache_id(self, key):
        # type: (str) -> str
        return '{}_{}'.format(self.check_id, key)

    def read_persistent_cache(self, key):
        # type: (str) -> str
        """Returns the value previously stored with `write_persistent_cache` for the same `key`.

        Parameters:
            key (str):
                the key to retrieve
        """
        return datadog_agent.read_persistent_cache(self._persistent_cache_id(key))

    def write_persistent_cache(self, key, value):
        # type: (str, str) -> None
        """Stores `value` in a persistent cache for this check instance.
        The cache is located in a path where the agent is guaranteed to have read & write permissions. Namely in
            - `%ProgramData%\\Datadog\\run` on Windows.
            - `/opt/datadog-agent/run` everywhere else.
        The cache is persistent between agent restarts but will be rebuilt if the check instance configuration changes.

        Parameters:
            key (str):
                the key to retrieve
            value (str):
                the value to store
        """
        datadog_agent.write_persistent_cache(self._persistent_cache_id(key), value)

    def set_external_tags(self, external_tags):
        # type: (Sequence[ExternalTagType]) -> None
        # Example of external_tags format
        # [
        #     ('hostname', {'src_name': ['test:t1']}),
        #     ('hostname2', {'src2_name': ['test2:t3']})
        # ]
        try:
            new_tags = []
            for hostname, source_map in external_tags:
                new_tags.append((to_native_string(hostname), source_map))
                for src_name, tags in source_map.items():
                    source_map[src_name] = self._normalize_tags_type(tags)
            datadog_agent.set_external_tags(new_tags)
        except IndexError:
            self.log.exception('Unexpected external tags format: %s', external_tags)
            raise

    def convert_to_underscore_separated(self, name):
        # type: (Union[str, bytes]) -> bytes
        """
        Convert from CamelCase to camel_case
        And substitute illegal metric characters
        """
        name = ensure_bytes(name)
        metric_name = self.FIRST_CAP_RE.sub(rb'\1_\2', name)
        metric_name = self.ALL_CAP_RE.sub(rb'\1_\2', metric_name).lower()
        metric_name = self.METRIC_REPLACEMENT.sub(rb'_', metric_name)
        return self.DOT_UNDERSCORE_CLEANUP.sub(rb'.', metric_name).strip(b'_')

    def warning(self, warning_message, *args, **kwargs):
        # type: (str, *Any, **Any) -> None
        """Log a warning message, display it in the Agent's status page and in-app.

        Using *args is intended to make warning work like log.warn/debug/info/etc
        and make it compliant with flake8 logging format linter.

        Parameters:
            warning_message (str):
                the warning message
            args (Any):
                format string args used to format the warning message e.g. `warning_message % args`
            kwargs (Any):
                not used for now, but added to match Python logger's `warning` method signature
        """
        warning_message = to_native_string(warning_message)
        # Interpolate message only if args is not empty. Same behavior as python logger:
        # https://github.com/python/cpython/blob/1dbe5373851acb85ba91f0be7b83c69563acd68d/Lib/logging/__init__.py#L368-L369
        if args:
            warning_message = warning_message % args
        frame = inspect.currentframe().f_back  # type: ignore
        lineno = frame.f_lineno
        # only log the last part of the filename, not the full path
        filename = basename(frame.f_code.co_filename)

        self.log.warning(warning_message, extra={'_lineno': lineno, '_filename': filename, '_check_id': self.check_id})
        self.warnings.append(warning_message)

    def get_warnings(self):
        # type: () -> List[str]
        """
        Return the list of warnings messages to be displayed in the info page
        """
        warnings = self.warnings
        self.warnings = []
        return warnings

    def get_diagnoses(self):
        # type: () -> str
        """
        Return the list of diagnosis as a JSON encoded string.

        The agent calls this method to retrieve diagnostics from integrations. This method
        runs explicit diagnostics if available.
        """
        return json.encode([d._asdict() for d in (self.diagnosis.diagnoses + self.diagnosis.run_explicit())])

    def _clear_diagnosis(self) -> None:
        if hasattr(self, '_diagnosis'):
            self._diagnosis.clear()

    def _get_requests_proxy(self):
        # type: () -> ProxySettings
        # TODO: Remove with Agent 5
        no_proxy_settings = {'http': None, 'https': None, 'no': []}  # type: ProxySettings

        # First we read the proxy configuration from datadog.conf
        proxies = self.agentConfig.get('proxy', datadog_agent.get_config('proxy'))
        if proxies:
            proxies = proxies.copy()

        # requests compliant dict
        if proxies and 'no_proxy' in proxies:
            proxies['no'] = proxies.pop('no_proxy')

        return proxies if proxies else no_proxy_settings

    def _format_namespace(self, s, raw=False):
        # type: (str, bool) -> str
        if not raw and self.__NAMESPACE__:
            return '{}.{}'.format(self.__NAMESPACE__, to_native_string(s))

        return to_native_string(s)

    def normalize(self, metric, prefix=None, fix_case=False):
        # type: (Union[str, bytes], Union[str, bytes], bool) -> str
        """
        Turn a metric into a well-formed metric name prefix.b.c

        Parameters:
            metric: The metric name to normalize
            prefix: A prefix to to add to the normalized name, default None
            fix_case: A boolean, indicating whether to make sure that the metric name returned is in "snake_case"
        """
        if isinstance(metric, str):
            metric = unicodedata.normalize('NFKD', metric).encode('ascii', 'ignore')

        if fix_case:
            name = self.convert_to_underscore_separated(metric)
            if prefix is not None:
                prefix = self.convert_to_underscore_separated(prefix)
        else:
            name = self.METRIC_REPLACEMENT.sub(rb'_', metric)
            name = self.DOT_UNDERSCORE_CLEANUP.sub(rb'.', name).strip(b'_')

        name = self.MULTIPLE_UNDERSCORE_CLEANUP.sub(rb'_', name)

        if prefix is not None:
            name = ensure_bytes(prefix) + b"." + name

        return to_native_string(name)

    def normalize_tag(self, tag):
        # type: (Union[str, bytes]) -> str
        """Normalize tag values.

        This happens for legacy reasons, when we cleaned up some characters (like '-')
        which are allowed in tags.
        """
        if isinstance(tag, str):
            tag = tag.encode('utf-8', 'ignore')
        tag = self.TAG_REPLACEMENT.sub(rb'_', tag)
        tag = self.MULTIPLE_UNDERSCORE_CLEANUP.sub(rb'_', tag)
        tag = self.DOT_UNDERSCORE_CLEANUP.sub(rb'.', tag).strip(b'_')
        return to_native_string(tag)

    def check(self, instance):
        # type: (InstanceType) -> None
        raise NotImplementedError

    def cancel(self):
        # type: () -> None
        """
        This method is called when the check in unscheduled by the agent. This
        is SIGNAL that the check is being unscheduled and can be called while
        the check is running. It's up to the python implementation to make sure
        cancel is thread safe and won't block.
        """
        pass

    def run(self):
        # type: () -> str
        try:
            self._clear_diagnosis()
            # Ignore check initializations if running in a separate process
            if is_affirmative(self.instance.get('process_isolation', self.init_config.get('process_isolation', False))):
                from datadog_checks.base.utils.replay.execute import run_with_isolation

                run_with_isolation(self, aggregator, datadog_agent)
            else:
                while self.check_initializations:
                    initialization = self.check_initializations.popleft()
                    try:
                        initialization()
                    except Exception:
                        self.check_initializations.appendleft(initialization)
                        raise

                instance = copy.deepcopy(self.instances[0])

                if 'set_breakpoint' in self.init_config:
                    from datadog_checks.base.utils.agent.debug import enter_pdb

                    enter_pdb(self.check, line=self.init_config['set_breakpoint'], args=(instance,))
                elif self.should_profile_memory():
                    # The 'profile_memory' key in self.init_config could be `/tmp/datadog-agent-memory-profiler*`
                    # that is generated by Datadog Agent.
                    # If we use `--m-dir` for `agent check` command, a hidden flag, it should be same as a given value.
                    namespaces = [self.init_config.get('profile_memory')]
                    for id in self.check_id.split(":"):
                        namespaces.append(id)
                    self.profile_memory(func=self.check, namespaces=namespaces, args=(instance,))
                else:
                    self.check(instance)

            error_report = ''
        except Exception as e:
            message = self.sanitize(str(e))
            tb = self.sanitize(traceback.format_exc())
            error_report = json.encode([{'message': message, 'traceback': tb}])
        finally:
            if self.metric_limiter:
                if is_affirmative(self.debug_metrics.get('metric_contexts', False)):
                    debug_metrics = self.metric_limiter.get_debug_metrics()

                    # Reset so we can actually submit the metrics
                    self.metric_limiter.reset()

                    tags = self.get_debug_metric_tags()
                    for metric_name, value in debug_metrics:
                        self.gauge(metric_name, value, tags=tags, raw=True)

                self.metric_limiter.reset()

        return error_report

    def event(self, event):
        # type: (Event) -> None
        """Send an event.

        An event is a dictionary with the following keys and data types:

        ```python
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
        ```

        Parameters:
            event (dict[str, Any]):
                the event to be sent
        """
        # Enforce types of some fields, considerably facilitates handling in go bindings downstream
        for key, value in event.items():
            if not isinstance(value, (str, bytes)):
                continue

            try:
                event[key] = to_native_string(value)  # type: ignore
                # ^ Mypy complains about dynamic key assignment -- arguably for good reason.
                # Ideally we should convert this to a dict literal so that submitted events only include known keys.
            except UnicodeError:
                self.log.warning('Encoding error with field `%s`, cannot submit event', key)
                return

        if event.get('tags'):
            event['tags'] = self._normalize_tags_type(event['tags'])
        if event.get('timestamp'):
            event['timestamp'] = int(event['timestamp'])
        if event.get('aggregation_key'):
            event['aggregation_key'] = to_native_string(event['aggregation_key'])

        if self.__NAMESPACE__:
            event.setdefault('source_type_name', self.__NAMESPACE__)

        aggregator.submit_event(self, self.check_id, event)

    def _normalize_tags_type(self, tags, device_name=None, metric_name=None):
        # type: (Sequence[Union[None, str, bytes]], str, str) -> List[str]
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
                normalized_tags.append('device:{}'.format(to_native_string(device_name)))
            except UnicodeError:
                self.log.warning(
                    'Encoding error with device name `%r` for metric `%r`, ignoring tag', device_name, metric_name
                )

        for tag in tags:
            if tag is None:
                continue
            try:
                tag = to_native_string(tag)
            except UnicodeError:
                self.log.warning('Encoding error with tag `%s` for metric `%s`, ignoring tag', tag, metric_name)
                continue
            if self.disable_generic_tags:
                normalized_tags.append(self.degeneralise_tag(tag))
            else:
                normalized_tags.append(tag)
        return normalized_tags

    def degeneralise_tag(self, tag):
        split_tag = tag.split(':', 1)
        if len(split_tag) > 1:
            tag_name, value = split_tag
        else:
            tag_name = tag
            value = None

        if tag_name in GENERIC_TAGS:
            new_name = '{}_{}'.format(self.name, tag_name)
            if value:
                return '{}:{}'.format(new_name, value)
            else:
                return new_name
        else:
            return tag

    def get_debug_metric_tags(self):
        tags = ['check_name:{}'.format(self.name), 'check_version:{}'.format(self.check_version)]
        tags.extend(self.instance.get('tags', []))
        return tags

    def get_memory_profile_tags(self):
        # type: () -> List[str]
        tags = self.get_debug_metric_tags()
        tags.extend(self.instance.get('__memory_profiling_tags', []))
        return tags

    def should_profile_memory(self):
        # type: () -> bool
        return 'profile_memory' in self.init_config or (
            datadog_agent.tracemalloc_enabled() and should_profile_memory(datadog_agent, self.name)
        )

    def profile_memory(self, func, namespaces=None, args=(), kwargs=None, extra_tags=None):
        # type: (Callable[..., Any], Optional[Sequence[str]], Sequence[Any], Optional[Dict[str, Any]], Optional[List[str]]) -> None  # noqa: E501
        from datadog_checks.base.utils.agent.memory import profile_memory

        if namespaces is None:
            namespaces = self.check_id.split(':', 1)

        tags = self.get_memory_profile_tags()
        if extra_tags is not None:
            tags.extend(extra_tags)

        metrics = profile_memory(func, self.init_config, namespaces=namespaces, args=args, kwargs=kwargs)

        for m in metrics:
            self.gauge(m.name, m.value, tags=tags, raw=True)

    @staticmethod
    def load_config(yaml_str: str) -> Any:
        """
        Convenience wrapper to ease programmatic use of this class from the C API.
        """
        import subprocess
        import sys

        process = subprocess.Popen(
            [sys.executable, '-c', 'import sys, yaml; print(yaml.safe_load(sys.stdin.read()))'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = process.communicate(yaml_str.encode())
        if process.returncode != 0:
            raise ValueError(f'Failed to load config: {stderr.decode()}')

        return _parse_ast_config(stdout.strip().decode())
