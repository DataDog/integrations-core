# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
import weakref

import pywintypes
import win32pdh

from ....errors import ConfigTypeError, ConfigValueError
from .constants import PDH_CSTATUS_INVALID_DATA, PDH_INVALID_DATA
from .transform import NATIVE_TRANSFORMERS, TRANSFORMERS
from .utils import construct_counter_path, get_counter_value, get_counter_values, validate_path


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

        # List of regex patterns to filter multi-instance counters AFTER ALL the data
        # is collected and retrieved from PDH layer
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

        # List of regex patterns to filter multi-instance counters AFTER ALL data
        # is collected and retrieved from PDH layer
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

        # List of wildcards or instance name directly to filter multi-instance counters by PDH layer itself.
        # Thus it is faster and and less resource intensive than regex-based include filtering.
        include_wildcards = config.get('include_fast', [])
        if not isinstance(include_wildcards, list):
            raise ConfigTypeError(f'Option `include_fast` for performance object `{self.name}` must be an array')
        elif not include_wildcards:
            self.include_wildcards = None
        else:
            for i, pattern in enumerate(include_wildcards, 1):
                if not isinstance(pattern, str):
                    raise ConfigTypeError(
                        f'Pattern #{i} of option `include_fast` for performance object `{self.name}` must be a string'
                    )

            self.include_wildcards = include_wildcards

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

        # Temporary and not documented, at least at this point, configuration value which controls which API
        # will be invoked to get multiple instance values. If the configuration is `true`
        # (duplicate_instances_exist: true), which is default, then we will invoke Windows
        # PdhGetFormattedCounterArrayW() API and process its output in pure Python. If not, we will invoke
        # win32pdh.GetFormattedCounterArray() which is 5-10x times faster than using
        # PdhGetFormattedCounterArrayW(), but it will lose duplicate/non-unique instances. There are a few
        # reasons for this configuration and its default value (true). Please note that PDH API calls
        # contribute only ~1% of overall performance overhead and making them 5-10x faster will not make
        # overall that much faster and most likely the gain will be lost in the non-deterministic noise. Still
        # these kind improvements are not wasteful:
        #
        #     * This new multi-instance wildcard-based implementation is 2-10+x faster than preceding
        #       per-instance based implementation (advantage is bigger the more instances and counters
        #       are involved). Thus the slower API calls are effectively on par regarding overall
        #       performance impact. It is true, its full performance advantage of wildcard-based
        #       implementation will not be realized until we can switch to an enhanced version of
        #       win32pdh.GetFormattedCounterArray(). Again, in overall performance overhead the gain
        #       will be small peanuts.
        #
        #     * We plan to file a ticket and perhaps assist to enhance win32pdh.GetFormattedCounterArray()
        #       function to handle non-unique instances. When it will be implemented we can remove slower
        #       Python implementation and this configuration variable along with it.
        #
        #     * In general, these calls are relatively fast. Typically they take microseconds or lower
        #       milliseconds (unless there are more than a few thousand instances). Multiplying by 10 will
        #       not make a drastic impact on overall performance since it may be call only every 15 seconds.
        #
        #     * Microsoft requests counter provider developers to avoid using duplicates. It is required
        #       for Performance Counters Provider V2 but it is not guaranteed in general for V1 counters.
        #       Microsoft's own counters seem to not allow duplicates with well known exceptions for
        #       "Process" performance objects. Even though it is a waste at this point in the virtual
        #       majority of the performance counters, since most of them will not have duplicate instance
        #       names to use the slower call which handles duplicates, still we would like to avoid changing
        #       default behavior and lose duplicates.
        #
        #     * This configuration at this point is provided just in case to have a fallback route if
        #       performance impact of the slower call could be problematic in some circumstances.
        #       To activate faster call, which cannot handle duplicate, use duplicate_instances_exist: false
        #
        #     * Because we are planning to pull out this configuration after relevant changes in win32pdh
        #       we are not planning at this time to make it public in the sense of adding it to configuration
        #       sample file, or explicitly documenting it elsewhere except perhaps internal Kb articles.
        self.duplicate_instances_exist = config.get('duplicate_instances_exist', True)
        if not isinstance(self.duplicate_instances_exist, bool):
            raise ConfigTypeError(
                f'Option `duplicate_instances_exist` for performance object `{self.name}` must be an true or false'
            )

        # We'll configure on the first run because it's necessary to figure out whether the
        # object contains single or multi-instance counters, see:
        # https://docs.microsoft.com/en-us/windows/win32/perfctrs/object-and-counter-design
        self.counters = []
        self.has_multiple_instances = False

    def collect(self):
        for counter in self.counters:
            try:
                counter.collect()
            except Exception as e:
                # If one counter fails to be collected we still should try to collect
                # the rest of the counters. Log the error and move on.
                self.logger.error(
                    'Error collecting counter `%s` for object `%s`: `%s`',
                    counter.name,
                    self.name,
                    e,
                )

        # Collect "instance" metrics directly from a MultiCounter counter object
        if self.has_multiple_instances and len(self.counters) > 0:
            counter = next(iter(self.counters))
            total_instance_count, monitored_instance_count, unique_instance_count = counter.get_instance_count()

            if self.instance_count_total_metric is not None:
                self.check.gauge(self.instance_count_total_metric, total_instance_count, tags=self.tags)
            if self.instance_count_monitored_metric is not None:
                self.check.gauge(self.instance_count_monitored_metric, monitored_instance_count, tags=self.tags)
            if self.instance_count_unique_metric is not None:
                self.check.gauge(self.instance_count_unique_metric, unique_instance_count, tags=self.tags)

    def refresh(self):
        # Counters configuration should run only once in the current implementation.
        #
        # Removed non-default edge case support of dynamic addition/removal of configured performance
        # counters. Even if a provider of a performance counter object, specified in our configuration,
        # is not running, as long as its provider has been installed/deployed on the box, that is all
        # needed for this integration. When the counter provider starts, Agent will discover its new
        # instances and report them as metrics correspondingly.
        #
        # However, if the provider is installed AFTER the agent starts running, this implementation
        # will not be able to automatically discover and use it. In some way it is a step back because
        # this ability had been added in 7.34 among few other very important changes including detection
        # of appearance and disappearance of performance counter instances, support for non-unique
        # instances and  localization support. In this release detection of newly registered performance
        # counters providers (and their objects and counters) is pulled out for the following reasons:
        #    * It does not appear that the feature was needed by customers
        #    * It adds non-insignificant complexity to the code
        #    * It relies on very slow and resource hungry PdhEnumObjects(refresh=TRUE) function.
        #    * It pretty much requires the agent process to be run as administrator or local system
        #      user (otherwise will generate a handful of error messages in the event log every time
        #      refresh run). Microsoft support confirmed it even though it is not documented.  It is
        #      difficult to explain to customers.
        #    * The logic of dynamically adding and removing counters handles to facilitate support appears
        #      to may cause memory leaks in some counters (documented at least for ASP.NET e.g.).
        # Perhaps in future if customers would really want that and are ready to deal with the caveats above
        # we can add it back.

        if not self.counters:
            self._configure_counters()
            if self.counters:
                for counter in self.counters:
                    try:
                        counter.refresh()
                    except Exception as e:
                        # If one counter fails to be refreshed (created) we still should try to refresh
                        # the rest of the counters. Log the error and move on.
                        self.logger.error(
                            'Error refreshing counter `%s` for object `%s`: `%s`',
                            counter.name,
                            self.name,
                            e,
                        )

    def clear(self):
        for counter in self.counters:
            try:
                counter.clear()
            except Exception as e:
                # If one counter fails to be cleared we still should try to clear
                # the rest of the counters. Log the error and move on.
                self.logger.error(
                    'Error clearing counter `%s` for object `%s`: `%s`',
                    counter.name,
                    self.name,
                    e,
                )

    def _configure_counters(self):
        if self.use_localized_counters:
            # https://docs.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhaddcountera
            # https://mhammond.github.io/pywin32/win32pdh__AddCounter_meth.html
            counter_selector = win32pdh.AddCounter
        else:
            # https://docs.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhaddenglishcountera
            # https://mhammond.github.io/pywin32/win32pdh__AddEnglishCounter_meth.html
            counter_selector = win32pdh.AddEnglishCounter

        # If a performance object and its counters are installed we will be able to determine its type.
        # If they are not installed yet (see comment in refresh() method) counter type determination
        # will fail. Moreover, it will continue to fail no matter how many times it is called even after
        # the missing performance object and its counters have been installed.
        counter_type = self._get_counters_type()
        if counter_type == MultiCounter:
            self.has_multiple_instances = True
        elif counter_type == SingleCounter:
            self.has_multiple_instances = False
        else:
            raise Exception(
                f'None of the specified counters for performance object `{self.name}` are installed.'
                'If the object name is localized make sure `use_localized_counters` is true'
            )

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
                        self.include_wildcards,
                        self.duplicate_instances_exist,
                        self,
                    )

        self.counters.extend(counters.values())

    def _get_counters_type(self):
        # Enumerate all counter to find if it is single or multiple instance counter
        # The very virst iteration should be sufficienmt, just in case enumerate all
        for i, entry in enumerate(self.counters_config, 1):
            if not isinstance(entry, dict):
                raise ConfigTypeError(
                    f'Entry #{i} of option `counters` for performance object `{self.name}` must be a mapping'
                )

            for counter_name, _ in entry.items():
                # Check for multi-instance counter path
                possible_path = construct_counter_path(
                    machine_name=self.connection.server,
                    object_name=self.name,
                    counter_name=counter_name,
                    instance_name='*',
                )
                if validate_path(self.connection.query_handle, self.use_localized_counters, possible_path):
                    self.logger.debug('Performance object `%s` is multi-instance counter', self.name)
                    return MultiCounter

                # Check for single-instance counter path
                possible_path = construct_counter_path(
                    machine_name=self.connection.server,
                    object_name=self.name,
                    counter_name=counter_name,
                )
                if validate_path(self.connection.query_handle, self.use_localized_counters, possible_path):
                    self.logger.debug('Performance object `%s` is single-instance counter', self.name)
                    return SingleCounter

        self.logger.warning('Performance object `%s` type is not detected', self.name)
        return None

    def get_custom_transformers(self):
        return {}

    # At least one derived class (IIS CompatibilityPerfObject(PerfObject)) relies on this
    # function call as callback for its own state management
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

    def handle_counter_value_error(self, error):
        # Counter requires at least 2 data points to return a meaningful value, see:
        # https://docs.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhgetformattedcountervalue#remarks
        #
        # https://github.com/mhammond/pywin32/blob/main/win32/src/PyWinTypesmodule.cpp#L278

        # PDH_INVALID_DATA error can normally happen only once for a single-instance counter
        # which requires two PdhCollectQueryData (typically for the "rate" or "delta" counters).
        # For multi-instances counters, because different API is used for collection, the
        # mirror error is PDH_CSTATUS_INVALID_DATA.
        #
        # It is not 100% clear if these errors may happen in other circumstances. Currently, we
        # do not track if one of these errors happens once or more. It is obviously Ok in the
        # former case but possibly problematic in the latter case. If these errors are
        # reported in the "Debug" logs again and again for the same counter, then the  "Debug"
        # log should be promoted to "Error" log (which we will do if we will find it in
        # production).
        if error.winerror != PDH_INVALID_DATA and error.winerror != PDH_CSTATUS_INVALID_DATA:
            raise

        self.logger.debug(
            'Waiting on another data point for counter `%s` of performance object `%s`',
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
        if self.counter_handle is not None:
            try:
                value = get_counter_value(self.counter_handle)
            except pywintypes.error as error:
                self.handle_counter_value_error(error)
            else:
                self.transformer(value, tags=self.tags)

    def refresh(self):
        if self.counter_handle is None:
            self.counter_handle = self.counter_selector(self.connection.query_handle, self.path)

    def clear(self):
        if self.counter_handle is None:
            return

        try:
            # https://docs.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhremovecounter
            # https://mhammond.github.io/pywin32/win32pdh__RemoveCounter_meth.html
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
        include_wildcards,
        duplicate_instances_exist,
        perf_obj,
    ):
        super().__init__(
            name, config, check, connection, object_name, metric_prefix, counter_selector, tags, custom_transformer
        )

        # Weak reference is used to avoid circular dependency and potentail memory leak
        self.perf_obj_weakref = weakref.ref(perf_obj)

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

        self.include_wildcards = include_wildcards
        self.duplicate_instances_exist = duplicate_instances_exist

        self.total_instance_count = 0
        self.monitored_instance_count = 0
        self.unique_instance_count = 0

        # All monitored counter handles keyed by the instance name
        self.instances = []

    def collect(self):
        # Instance tracking is conducted for each counter although collected only from one.
        # This counting is cheap but making it conditional here will only complicate this method
        self.total_instance_count = 0
        self.monitored_instance_count = 0
        self.unique_instance_count = 0

        total = 0
        for counter_handle in self.instances:
            try:
                instance_items = get_counter_values(counter_handle, self.duplicate_instances_exist)

                for instance, value in instance_items.items():
                    # Some instances may not have a value yet, so we only
                    # use the ones that do for computing averages
                    instance_non_unique_count = 0
                    instance_total = 0

                    self.total_instance_count += 1
                    if self._instance_excluded(instance):
                        continue

                    self.unique_instance_count += 1

                    # Enumerate non-unique instances
                    if isinstance(value, list):
                        for sub_value in value:
                            instance_total += sub_value
                            instance_non_unique_count += 1
                    else:
                        instance_total = value
                        instance_non_unique_count += 1

                    if self.aggregate != 'only':
                        tags = [f'{self.tag_name}:{instance}']
                        tags.extend(self.tags)

                        if self.average:
                            self.transformer(instance_total / instance_non_unique_count, tags=tags)
                        else:
                            self.transformer(instance_total, tags=tags)

                    if not instance_non_unique_count:
                        continue

                    self.monitored_instance_count += instance_non_unique_count
                    total += instance_total

            except pywintypes.error as error:
                self.handle_counter_value_error(error)
            except KeyError:
                # To support IIS mocking tests for non-existing wildcard counters
                pass

        if not self.monitored_instance_count:
            return

        if self.aggregate is not False:
            if self.average:
                self.aggregate_transformer(total / self.monitored_instance_count, tags=self.tags)
            else:
                self.aggregate_transformer(total, tags=self.tags)

    def refresh(self):
        # No need to create a counter handle or handles if they already exist. And since new
        # counters for a performance object can be detected (without PdhEnumObjects(refresh=True))
        # there is no point to make sure that all counters are available.
        if self.instances and len(self.instances) > 0:
            return

        self.instances = []
        if self.include_wildcards is None:
            self.include_wildcards = ["*"]

        for _, pattern in enumerate(self.include_wildcards, 1):
            path = construct_counter_path(
                machine_name=self.connection.server,
                object_name=self.object_name,
                counter_name=self.name,
                instance_name=pattern,
            )

            counter_handle = self.counter_selector(self.connection.query_handle, path)
            self.instances.append(counter_handle)

    def clear(self):
        if not self.instances:
            return

        for counter_handle in self.instances:
            try:
                # https://docs.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhremovecounter
                # https://mhammond.github.io/pywin32/win32pdh__RemoveCounter_meth.html
                win32pdh.RemoveCounter(counter_handle)
            except Exception as e:
                self.logger.warning(
                    'Unable to remove handle for counter `%s` of performance object `%s`: %s',
                    self.name,
                    self.object_name,
                    e,
                )

        self.instances.clear()

    def get_instance_count(self):
        return self.total_instance_count, self.monitored_instance_count, self.unique_instance_count

    def _instance_excluded(self, instance):
        # There is no need for additional validation since call to this object
        # is always done from the live parent object (perf_obj)
        perf_obj = self.perf_obj_weakref()
        return perf_obj._instance_excluded(instance)
