# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from collections import defaultdict

import pywintypes
import win32pdh

from ....errors import ConfigTypeError, ConfigValueError
from .transform import NATIVE_TRANSFORMERS, TRANSFORMERS
from .utils import construct_counter_path, format_instance, get_counter_value


class PerfObject:
    def __init__(self, check, connection, name, config, use_localized_counters, tags):
        self.check = check
        self.logger = check.log
        self.connection = connection
        self.use_localized_counters = config.get('use_localized_counters', use_localized_counters)
        self.tags = tags

        # The name of the performance object e.g. System
        self.name = name

        # The prefix of all metrics
        self.metric_prefix = config.get('name', '')
        if not isinstance(self.metric_prefix, str):
            raise ConfigTypeError(f'Option `name` for performance object `{self.name}` must be a string')
        elif not self.metric_prefix:
            raise ConfigValueError(f'Option `name` for performance object `{self.name}` is required')

        # The tag name used for any instances
        self.tag_name = config.get('tag_name', '')
        if not isinstance(self.tag_name, str):
            raise ConfigTypeError(f'Option `tag_name` for performance object `{self.name}` must be a string')

        include_patterns = config.get('include', [])
        if not isinstance(include_patterns, list):
            raise ConfigTypeError(f'Option `include` for performance object `{self.name}` must be an array')
        elif not include_patterns:
            self.include_pattern = None
        else:
            for i, pattern in enumerate(include_patterns, 1):
                if not isinstance(pattern, str):
                    raise ConfigTypeError(
                        f'Pattern #{i} of option `include` for performance object `{self.name}` must be a string'
                    )

            self.include_pattern = re.compile('|'.join(include_patterns))

        exclude_patterns = config.get('exclude', [])
        if not isinstance(exclude_patterns, list):
            raise ConfigTypeError(f'Option `exclude` for performance object `{self.name}` must be an array')
        else:
            for i, pattern in enumerate(exclude_patterns, 1):
                if not isinstance(pattern, str):
                    raise ConfigTypeError(
                        f'Pattern #{i} of option `exclude` for performance object `{self.name}` must be a string'
                    )

            final_exclude_patterns = [r'\b_Total\b']
            final_exclude_patterns.extend(exclude_patterns)
            self.exclude_pattern = re.compile('|'.join(final_exclude_patterns))

        instance_counts = config.get('instance_counts', {})
        if not isinstance(instance_counts, dict):
            raise ConfigTypeError(f'Option `instance_counts` for performance object `{self.name}` must be a mapping')

        unknown_count_types = set(instance_counts) - {'total', 'monitored', 'unique'}
        if unknown_count_types:
            raise ConfigValueError(
                f'Option `instance_counts` for performance object `{self.name}` has unknown types: '
                f'{", ".join(sorted(unknown_count_types))}'
            )

        for count_type, metric_name in instance_counts.items():
            if not isinstance(metric_name, str):
                raise ConfigTypeError(
                    f'Metric name for count type `{count_type}` of option `instance_counts` for performance object '
                    f'`{self.name}` must be a string'
                )

        self.instance_count_total_metric = instance_counts.get('total')
        self.instance_count_monitored_metric = instance_counts.get('monitored')
        self.instance_count_unique_metric = instance_counts.get('unique')

        self.counters_config = config.get('counters', [])
        if not isinstance(self.counters_config, list):
            raise ConfigTypeError(f'Option `counters` for performance object `{self.name}` must be an array')
        elif not self.counters_config:
            raise ConfigValueError(f'Option `counters` for performance object `{self.name}` is required')

        # We'll configure on the first run because it's necessary to figure out whether the
        # object contains single or multi-instance counters, see:
        # https://docs.microsoft.com/en-us/windows/win32/perfctrs/object-and-counter-design
        self.counters = []
        self.has_multiple_instances = False

    def collect(self):
        for counter in self.counters:
            counter.collect()

    def refresh(self):
        # https://docs.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhenumobjectitemsa
        # http://timgolden.me.uk/pywin32-docs/win32pdh__EnumObjectItems_meth.html
        counters, instances = win32pdh.EnumObjectItems(
            None, self.connection.server, self.name, win32pdh.PERF_DETAIL_WIZARD
        )
        if not self.counters:
            self._configure_counters(counters, instances)

        counters = set(counters)
        total_instance_count = 0
        monitored_instance_count = 0
        unique_instance_counts = defaultdict(int)
        for instance in instances:
            total_instance_count += 1
            if self._instance_excluded(instance):
                continue

            monitored_instance_count += 1
            unique_instance_counts[instance] += 1

        if self.has_multiple_instances:
            if self.instance_count_total_metric is not None:
                self.check.gauge(self.instance_count_total_metric, total_instance_count, tags=self.tags)
            if self.instance_count_monitored_metric is not None:
                self.check.gauge(self.instance_count_monitored_metric, monitored_instance_count, tags=self.tags)
            if self.instance_count_unique_metric is not None:
                self.check.gauge(self.instance_count_unique_metric, len(unique_instance_counts), tags=self.tags)

        for counter in self.counters:
            if counter.name not in counters:
                self.logger.error(
                    'Did not find expected counter `%s` of performance object `%s`', counter.name, self.name
                )
                counter.clear()
            else:
                counter.refresh(unique_instance_counts)

    def clear(self):
        for counter in self.counters:
            counter.clear()

    def _configure_counters(self, available_counters, available_instances):
        if not available_counters:
            return

        if self.use_localized_counters:
            # https://docs.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhaddcountera
            # http://timgolden.me.uk/pywin32-docs/win32pdh__AddCounter_meth.html
            counter_selector = win32pdh.AddCounter
        else:
            # https://docs.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhaddenglishcountera
            # http://timgolden.me.uk/pywin32-docs/win32pdh__AddEnglishCounter_meth.html
            counter_selector = win32pdh.AddEnglishCounter

        if available_instances:
            counter_type = MultiCounter
            self.has_multiple_instances = True
        else:
            possible_path = construct_counter_path(
                machine_name=self.connection.server, object_name=self.name, counter_name=available_counters[0]
            )

            # https://docs.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhvalidatepatha
            # http://timgolden.me.uk/pywin32-docs/win32pdh__ValidatePath_meth.html
            if win32pdh.ValidatePath(possible_path) == 0:
                counter_type = SingleCounter
                self.has_multiple_instances = False
            # Multi-instance counter with no instances presently
            else:
                counter_type = MultiCounter
                self.has_multiple_instances = True

        tag_name = self.tag_name
        if self.has_multiple_instances:
            if not tag_name:
                tag_name = 'instance'
        else:
            if tag_name:
                self._log_multi_instance_option_defined('tag_name')
            if self.include_pattern is not None:
                self._log_multi_instance_option_defined('include')
            if self.exclude_pattern.pattern.count('|') > 0:
                self._log_multi_instance_option_defined('exclude')
            if (
                self.instance_count_total_metric
                or self.instance_count_monitored_metric
                or self.instance_count_unique_metric
            ):
                self._log_multi_instance_option_defined('instance_counts')

        custom_transformers = self.get_custom_transformers()
        counters = {}
        for i, entry in enumerate(self.counters_config, 1):
            if not isinstance(entry, dict):
                raise ConfigTypeError(
                    f'Entry #{i} of option `counters` for performance object `{self.name}` must be a mapping'
                )

            for counter_name, counter_config in entry.items():
                if isinstance(counter_config, str):
                    counter_config = {'name': counter_config}
                elif not isinstance(counter_config, dict):
                    raise ConfigTypeError(
                        f'Counter `{counter_name}` for performance object `{self.name}` must be a string or mapping'
                    )
                elif counter_name in counters:
                    raise ConfigValueError(
                        f'Counter `{counter_name}` for performance object `{self.name}` is already defined'
                    )

                if counter_type is SingleCounter:
                    counters[counter_name] = counter_type(
                        counter_name,
                        counter_config,
                        self.check,
                        self.connection,
                        self.name,
                        self.metric_prefix,
                        counter_selector,
                        self.tags,
                        custom_transformers.get(counter_name),
                    )
                else:
                    counters[counter_name] = counter_type(
                        counter_name,
                        counter_config,
                        self.check,
                        self.connection,
                        self.name,
                        self.metric_prefix,
                        counter_selector,
                        self.tags,
                        custom_transformers.get(counter_name),
                        tag_name,
                    )

        self.counters.extend(counters.values())

    def get_custom_transformers(self):
        return {}

    def _instance_excluded(self, instance):
        return self.exclude_pattern.search(instance) or (
            self.include_pattern is not None and not self.include_pattern.search(instance)
        )

    def _log_multi_instance_option_defined(self, option_name):
        self.logger.warning(
            'Ignoring option `%s` for performance object `%s` since it contains single instance counters',
            option_name,
            self.name,
        )


class CounterBase:
    def __init__(
        self, name, config, check, connection, object_name, metric_prefix, counter_selector, tags, custom_transformer
    ):
        self.logger = check.log
        self.connection = connection
        self.counter_selector = counter_selector
        self.tags = tags

        # The name of the counter e.g. System Calls/sec
        self.name = name

        # The name of the performance object e.g. System
        self.object_name = object_name

        self.metric_name = config.get('metric_name', '')
        if not isinstance(self.metric_name, str):
            raise ConfigTypeError(
                f'Option `metric_name` for counter `{self.name}` of performance object '
                f'`{self.object_name}` must be a string'
            )
        elif not self.metric_name:
            metric_suffix = config.get('name', '')
            if not isinstance(metric_suffix, str):
                raise ConfigTypeError(
                    f'Option `name` for counter `{self.name}` of performance object '
                    f'`{self.object_name}` must be a string'
                )
            elif not metric_suffix:
                raise ConfigValueError(
                    f'Option `name` for counter `{self.name}` of performance object `{self.object_name}` is required'
                )

            self.metric_name = f'{metric_prefix}.{metric_suffix}'

        if custom_transformer is not None:
            self.metric_type = 'custom'
            self.transformer = custom_transformer(check, self.metric_name, config)
        else:
            self.metric_type = config.get('type', 'gauge')
            if not isinstance(self.metric_type, str):
                raise ConfigTypeError(
                    f'Option `type` for counter `{self.name}` of performance object '
                    f'`{self.object_name}` must be a string'
                )
            elif self.metric_type not in TRANSFORMERS:
                raise ConfigValueError(
                    f'Unknown `type` for counter `{self.name}` of performance object `{self.object_name}`'
                )

            try:
                self.transformer = TRANSFORMERS[self.metric_type](check, self.metric_name, config)
            except Exception as e:
                error = (
                    f'Error compiling transformer for counter `{self.name}` of performance object '
                    f'`{self.object_name}`: {e}'
                )
                raise type(e)(error) from None

    def handle_counter_value_error(self, error, instance=None):
        # Counter requires at least 2 data points to return a meaningful value, see:
        # https://docs.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhgetformattedcountervalue#remarks
        #
        # http://timgolden.me.uk/pywin32-docs/error.html
        if error.strerror != 'The data is not valid.':
            raise

        if instance is None:
            self.logger.debug(
                'Waiting on another data point for counter `%s` of performance object `%s`',
                self.name,
                self.object_name,
            )
        else:
            self.logger.debug(
                'Waiting on another data point for instance `%s` of counter `%s` of performance object `%s`',
                instance,
                self.name,
                self.object_name,
            )


class SingleCounter(CounterBase):
    def __init__(
        self, name, config, check, connection, object_name, metric_prefix, counter_selector, tags, custom_transformer
    ):
        super().__init__(
            name, config, check, connection, object_name, metric_prefix, counter_selector, tags, custom_transformer
        )

        self.path = construct_counter_path(
            machine_name=self.connection.server, object_name=self.object_name, counter_name=self.name
        )
        self.counter_handle = None

    def collect(self):
        try:
            value = get_counter_value(self.counter_handle)
        except pywintypes.error as error:
            self.handle_counter_value_error(error)
        else:
            self.transformer(value, tags=self.tags)

    def refresh(self, _):
        if self.counter_handle is None:
            self.counter_handle = self.counter_selector(self.connection.query_handle, self.path)

    def clear(self):
        if self.counter_handle is None:
            return

        try:
            # https://docs.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhremovecounter
            # http://timgolden.me.uk/pywin32-docs/win32pdh__RemoveCounter_meth.html
            win32pdh.RemoveCounter(self.counter_handle)
        except Exception as e:
            self.logger.warning(
                'Unable to remove handle for counter `%s` of performance object `%s`: %s',
                self.name,
                self.object_name,
                e,
            )

        self.counter_handle = None


class MultiCounter(CounterBase):
    def __init__(
        self,
        name,
        config,
        check,
        connection,
        object_name,
        metric_prefix,
        counter_selector,
        tags,
        custom_transformer,
        tag_name,
    ):
        super().__init__(
            name, config, check, connection, object_name, metric_prefix, counter_selector, tags, custom_transformer
        )

        self.tag_name = tag_name

        self.average = config.get('average', False)
        if not isinstance(self.average, bool):
            raise ConfigTypeError(
                f'Option `average` for counter `{self.name}` of performance '
                f'object `{self.object_name}` must be a boolean'
            )

        self.aggregate_transformer = None
        self.aggregate = config.get('aggregate', False)
        if not isinstance(self.aggregate, bool) and self.aggregate != 'only':
            raise ConfigTypeError(
                f'Option `aggregate` for counter `{self.name}` of performance '
                f'object `{self.object_name}` must be a boolean or set to `only`'
            )
        elif self.aggregate is not False:
            if self.metric_type not in NATIVE_TRANSFORMERS:
                raise ConfigTypeError(
                    f'Option `aggregate` for counter `{self.name}` of performance object `{self.object_name}` is '
                    f'enabled so `type` must be set to one of the following: {", ".join(NATIVE_TRANSFORMERS)}'
                )
            else:
                metric_name = f'{self.metric_name}.avg' if self.average else f'{self.metric_name}.sum'
                self.aggregate_transformer = NATIVE_TRANSFORMERS[self.metric_type](check, metric_name, config)

        # All monitored counter handles keyed by the instance name
        self.instances = {}

    def collect(self):
        handles_with_data = 0
        total = 0
        for instance, counter_handles in self.instances.items():
            # Some instances may not have a value yet, so we only
            # use the ones that do for computing averages
            instance_handles_with_data = len(counter_handles)
            instance_total = 0

            for i, counter_handle in enumerate(counter_handles):
                try:
                    value = get_counter_value(counter_handle)
                except pywintypes.error as error:
                    instance_handles_with_data -= 1
                    self.handle_counter_value_error(error, format_instance(instance, i))
                else:
                    instance_total += value

            if not instance_handles_with_data:
                continue

            handles_with_data += instance_handles_with_data
            total += instance_total

            if self.aggregate != 'only':
                tags = [f'{self.tag_name}:{instance}']
                tags.extend(self.tags)

                if self.average:
                    self.transformer(instance_total / instance_handles_with_data, tags=tags)
                else:
                    self.transformer(instance_total, tags=tags)

        if not handles_with_data:
            return

        if self.aggregate is not False:
            if self.average:
                self.aggregate_transformer(total / handles_with_data, tags=self.tags)
            else:
                self.aggregate_transformer(total, tags=self.tags)

    def refresh(self, instance_counts):
        old_instances = self.instances
        new_instances = {}

        for instance, current_count in instance_counts.items():
            if instance in old_instances:
                counter_handles = old_instances.pop(instance)
                new_instances[instance] = counter_handles
                old_count = len(counter_handles)

                if current_count > old_count:
                    for index in range(old_count, current_count):
                        path = construct_counter_path(
                            machine_name=self.connection.server,
                            object_name=self.object_name,
                            counter_name=self.name,
                            instance_name=instance,
                            instance_index=index,
                        )
                        counter_handle = self.counter_selector(self.connection.query_handle, path)
                        counter_handles.append(counter_handle)
                elif current_count < old_count:
                    for _ in range(old_count - current_count):
                        counter_handle = counter_handles.pop()

                        try:
                            # https://docs.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhremovecounter
                            # http://timgolden.me.uk/pywin32-docs/win32pdh__RemoveCounter_meth.html
                            win32pdh.RemoveCounter(counter_handle)
                        except Exception as e:
                            self.logger.warning(
                                'Unable to remove handle for instance `%s` of counter `%s` '
                                'of performance object `%s`: %s',
                                format_instance(instance, len(counter_handles)),
                                self.name,
                                self.object_name,
                                e,
                            )
            else:
                counter_handles = []
                new_instances[instance] = counter_handles

                for index in range(current_count):
                    path = construct_counter_path(
                        machine_name=self.connection.server,
                        object_name=self.object_name,
                        counter_name=self.name,
                        instance_name=instance,
                        instance_index=index,
                    )
                    counter_handle = self.counter_selector(self.connection.query_handle, path)
                    counter_handles.append(counter_handle)

        # Remove expired instances
        self.clear()

        self.instances = new_instances

    def clear(self):
        if not self.instances:
            return

        for instance, counter_handles in self.instances.items():
            while counter_handles:
                counter_handle = counter_handles.pop()
                try:
                    # https://docs.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhremovecounter
                    # http://timgolden.me.uk/pywin32-docs/win32pdh__RemoveCounter_meth.html
                    win32pdh.RemoveCounter(counter_handle)
                except Exception as e:
                    self.logger.warning(
                        'Unable to remove handle for instance `%s` of counter `%s` of performance object `%s`: %s',
                        format_instance(instance, len(counter_handles)),
                        self.name,
                        self.object_name,
                        e,
                    )

        self.instances.clear()
