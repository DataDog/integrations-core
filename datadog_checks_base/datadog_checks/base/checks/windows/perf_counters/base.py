# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
# TODO: when we stop invoking Mypy with --py2, remove ignore and use f-strings
# type: ignore
from collections import ChainMap
from contextlib import contextmanager, suppress

import pywintypes
import win32pdh

from ....config import is_affirmative
from ....errors import ConfigTypeError, ConfigurationError
from ....utils.functions import raise_exception
from ... import AgentCheck
from .connection import Connection
from .counter import PerfObject


class PerfCountersBaseCheck(AgentCheck):
    SERVICE_CHECK_HEALTH = 'windows.perf.health'

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)

        self.enable_health_service_check = is_affirmative(self.instance.get('enable_health_service_check', True))

        # Prevent overriding an integration's defined namespace
        self.namespace = self.__NAMESPACE__ or self.instance.get('namespace', '')

        # All configured performance objects
        self.perf_objects = []

        # Shared by all performance objects
        self._connection = None

        # Submitted with everything
        self._static_tags = None

        self.check_initializations.append(self.create_connection)

        self.check_initializations.append(self.configure_perf_objects)

    def check(self, _):
        self.query_counters()

    def query_counters(self):
        with self.adopt_namespace(self.namespace):
            self._query_counters()

    def _query_counters(self):
        # Avoid collection of performance objects that failed to refresh
        collection_queue = []

        for perf_object in self.perf_objects:
            self.log.debug('Refreshing counters for performance object: %s', perf_object.name)
            try:
                perf_object.refresh()
            except ConfigurationError as e:
                # Counters are lazily configured and any errors should prevent check execution
                exception_class = type(e)
                message = str(e)
                self.check_initializations.append(
                    lambda exception_class=exception_class, message=message: raise_exception(exception_class, message)
                )
                return
            except Exception as e:
                self.log.error('Error refreshing counters for performance object `%s`: %s', perf_object.name, e)
            else:
                collection_queue.append(perf_object)

        try:
            # https://docs.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhcollectquerydata
            # https://mhammond.github.io/pywin32/win32pdh__CollectQueryData_meth.html
            win32pdh.CollectQueryData(self._connection.query_handle)
        except pywintypes.error as error:
            message = 'Error querying performance counters: {}'.format(error.strerror)
            self.submit_health_check(self.CRITICAL, message=message)
            self.log.error(message)
            return

        for perf_object in collection_queue:
            self.log.debug('Collecting query data for performance object: %s', perf_object.name)
            try:
                perf_object.collect()
            except Exception as e:
                self.log.error('Error collecting query data for performance object `%s`: %s', perf_object.name, e)

        self.submit_health_check(self.OK)

    def configure_perf_objects(self):
        perf_objects = []
        config = self.get_config_with_defaults()
        server_tag = config.get('server_tag') or 'server'
        use_localized_counters = is_affirmative(self.init_config.get('use_localized_counters', False))
        tags = ['{}:{}'.format(server_tag, self._connection.server)]
        tags.extend(config.get('tags', []))
        self._static_tags = tuple(tags)

        for option_name in ('metrics', 'extra_metrics'):
            metric_config = config.get(option_name, {})
            if not isinstance(metric_config, dict):
                raise ConfigTypeError('Setting `{}` must be a mapping'.format(option_name))

            for object_name, object_config in metric_config.items():
                if not isinstance(object_config, dict):
                    raise ConfigTypeError(
                        'Performance object `{}` in setting `{}` must be a mapping'.format(object_name, option_name)
                    )

                perf_object = self.get_perf_object(
                    self._connection, object_name, object_config, use_localized_counters, self._static_tags
                )
                perf_objects.append(perf_object)

        self.perf_objects.clear()
        self.perf_objects.extend(perf_objects)

    def create_connection(self):
        self._connection = Connection(self.instance)
        self.log.debug('Setting `server` to `%s`', self._connection.server)
        self._connection.connect()

    def get_perf_object(self, connection, object_name, object_config, use_localized_counters, tags):
        return PerfObject(self, connection, object_name, object_config, use_localized_counters, tags)

    def get_config_with_defaults(self):
        return ChainMap(self.instance, self.get_default_config())

    def get_default_config(self):
        return {}

    def submit_health_check(self, status, **kwargs):
        if self.enable_health_service_check:
            self.service_check(self.SERVICE_CHECK_HEALTH, status, tags=self._static_tags, **kwargs)

    @contextmanager
    def adopt_namespace(self, namespace):
        old_namespace = self.__NAMESPACE__

        try:
            self.__NAMESPACE__ = namespace
            yield
        finally:
            self.__NAMESPACE__ = old_namespace

    def cancel(self):
        for perf_object in self.perf_objects:
            with suppress(Exception):
                perf_object.clear()

        self._connection.disconnect()


class PerfCountersBaseCheckWithLegacySupport(PerfCountersBaseCheck):
    def get_config_with_defaults(self):
        default_config = super().get_config_with_defaults()
        updated_config = {}

        if 'host' in self.instance:
            updated_config['server'] = self.instance['host']

        has_legacy_metrics_config = False
        for option, new_option in (('metrics', 'metrics'), ('additional_metrics', 'extra_metrics')):
            # Legacy metrics were defined as a list of lists
            if option not in self.instance or not isinstance(self.instance[option], list):
                continue

            has_legacy_metrics_config = True
            metrics = {}

            enumeration = enumerate(self.instance[option], 1)
            for i, (object_name, instance, counter_name, metric_name, metric_type) in enumeration:
                if instance:
                    self.log.warning('Ignoring instance for entry #%s of option `%s`', i, option)

                object_config = metrics.setdefault(object_name, {'name': '__unused__', 'counters': []})
                object_config['counters'].append({counter_name: {'metric_name': metric_name, 'type': metric_type}})

            updated_config[new_option] = metrics

        if has_legacy_metrics_config and self.__NAMESPACE__:
            if 'metrics' in default_config and 'metrics' not in updated_config:
                metrics_config = updated_config['metrics'] = {}
                for object_name, config in default_config['metrics'].items():
                    new_config = config.copy()
                    new_config['name'] = '{}.{}'.format(self.__NAMESPACE__, new_config['name'])
                    metrics_config[object_name] = new_config

            # Ensure idempotency in case this method is called multiple times due to configuration errors
            if self.namespace:
                self.SERVICE_CHECK_HEALTH = '{}.{}'.format(self.__NAMESPACE__, self.SERVICE_CHECK_HEALTH)

            self.namespace = ''

        return default_config.new_child(updated_config)
