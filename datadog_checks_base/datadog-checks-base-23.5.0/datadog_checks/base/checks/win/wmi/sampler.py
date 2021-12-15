# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# flake8: noqa

"""
A lightweight Python WMI module wrapper built on top of `pywin32` and `win32com` extensions.

**Specifications**
* Based on top of the `pywin32` and `win32com` third party extensions only
* Compatible with `Raw`* and `Formatted` Performance Data classes
    * Dynamically resolve properties' counter types
    * Hold the previous/current `Raw` samples to compute/format new values*
* Fast and lightweight
    * Avoid queries overhead
    * Cache connections and qualifiers
    * Use `wbemFlagForwardOnly` flag to improve enumeration/memory performance

*\* `Raw` data formatting relies on the avaibility of the corresponding calculator.
Please refer to `checks.lib.wmi.counter_type` for more information*

Original discussion thread: https://github.com/DataDog/dd-agent/issues/1952
Credits to @TheCloudlessSky (https://github.com/TheCloudlessSky)
"""
from copy import deepcopy
from threading import Event, Thread

import pythoncom
import pywintypes
from six import iteritems, string_types, with_metaclass
from six.moves import zip
from win32com.client import Dispatch

from .counter_type import UndefinedCalculator, get_calculator, get_raw


class CaseInsensitiveDict(dict):
    def __setitem__(self, key, value):
        super(CaseInsensitiveDict, self).__setitem__(key.lower(), value)

    def __getitem__(self, key):
        return super(CaseInsensitiveDict, self).__getitem__(key.lower())

    def __contains__(self, key):
        return super(CaseInsensitiveDict, self).__contains__(key.lower())

    def get(self, key):
        return super(CaseInsensitiveDict, self).get(key.lower())

    def copy(self):
        """
        Explicit copy to ensure we return an instance of `CaseInsensitiveDict`
        """
        return CaseInsensitiveDict(self)


class ProviderArchitectureMeta(type):
    """
    Metaclass for ProviderArchitecture.
    """

    def __contains__(cls, provider):
        """
        Support `Enum` style `contains`.
        """
        return provider in cls._AVAILABLE_PROVIDER_ARCHITECTURES


class ProviderArchitecture(with_metaclass(ProviderArchitectureMeta, object)):
    """
    Enumerate WMI Provider Architectures.
    """

    # Available Provider Architecture(s)
    DEFAULT = 0
    _32BIT = 32
    _64BIT = 64
    _AVAILABLE_PROVIDER_ARCHITECTURES = frozenset([DEFAULT, _32BIT, _64BIT])


class WMISampler(object):
    """
    WMI Sampler.
    """

    def __init__(
        self,
        logger,
        class_name,
        property_names,
        filters="",
        host="localhost",
        namespace="root\\cimv2",
        provider=None,
        username="",
        password="",
        and_props=None,
        timeout_duration=10,
    ):
        # Properties
        self._provider = None
        self._formatted_filters = None

        # Type resolution state
        self._property_counter_types = None

        # Samples
        self._current_sample = None
        self._previous_sample = None

        # Sampling state
        self._sampling = False
        self._stopping = False

        self.logger = logger

        # Connection information
        self.host = host
        self.namespace = namespace
        self.provider = provider
        self.username = username
        self.password = password

        self.is_raw_perf_class = "_PERFRAWDATA_" in class_name.upper()

        # Sampler settings
        #   WMI class, properties, filters and counter types
        #   Include required properties for making calculations with raw
        #   performance counters:
        #   https://msdn.microsoft.com/en-us/library/aa394299(v=vs.85).aspx
        if self.is_raw_perf_class:
            property_names.extend(
                [
                    "Timestamp_Sys100NS",
                    "Frequency_Sys100NS",
                    # IMPORTANT: To improve performance and since they're currently
                    # not needed, do not include the other Timestamp/Frequency
                    # properties:
                    #   - Timestamp_PerfTime
                    #   - Timestamp_Object
                    #   - Frequency_PerfTime
                    #   - Frequency_Object"
                ]
            )

        self.class_name = class_name
        self.property_names = property_names
        self.filters = filters
        self._and_props = and_props if and_props is not None else []
        self._timeout_duration = timeout_duration

        self._runSampleEvent = Event()
        self._sampleCompleteEvent = Event()
        self._sampler_thread = None

    def start(self):
        """
        Start internal thread for sampling
        """
        self._sampler_thread = Thread(target=self._query_sample_loop, name=self.class_name)
        self._sampler_thread.daemon = True  # Python 2 does not support daemon as Thread constructor parameter
        self._sampler_thread.start()

    def stop(self):
        """
        Dispose of the internal thread
        """
        self._stopping = True
        self._runSampleEvent.set()
        self._sampleCompleteEvent.wait()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, traceback):
        self.stop()

    def _query_sample_loop(self):
        try:
            # Initialize COM for the current (dedicated) thread
            # WARNING: any python COM object (locator, connection, etc) created in a thread
            # shouldn't be used in other threads (can lead to memory/handle leaks if done
            # without a deep knowledge of COM's threading model).
            pythoncom.CoInitialize()
        except Exception as e:
            self.logger.info("exception in CoInitialize: %s", e)
            raise

        while True:
            self._runSampleEvent.wait()
            if self._stopping:
                self.logger.debug("_query_sample_loop stopping")
                self._sampleCompleteEvent.set()
                return

            self._runSampleEvent.clear()
            if self.is_raw_perf_class and not self._previous_sample:
                self._current_sample = self._query()

            self._previous_sample = self._current_sample
            self._current_sample = self._query()
            self._sampleCompleteEvent.set()

    @property
    def provider(self):
        """
        Return the WMI provider.
        """
        return self._provider

    @provider.setter
    def provider(self, value):
        """
        Validate and set a WMI provider. Default to `ProviderArchitecture.DEFAULT`
        """
        result = None

        # `None` defaults to `ProviderArchitecture.DEFAULT`
        defaulted_value = value or ProviderArchitecture.DEFAULT

        try:
            parsed_value = int(defaulted_value)
        except ValueError:
            pass
        else:
            if parsed_value in ProviderArchitecture:
                result = parsed_value

        if result is None:
            self.logger.error(u"Invalid '%s' WMI Provider Architecture. The parameter is ignored.", value)

        self._provider = result or ProviderArchitecture.DEFAULT

    @property
    def connection(self):
        """
        A property to retrieve the sampler connection information.
        """
        return {'host': self.host, 'namespace': self.namespace, 'username': self.username, 'password': self.password}

    @property
    def connection_key(self):
        """
        Return an index key used to cache the sampler connection.
        """
        return "{host}:{namespace}:{username}".format(host=self.host, namespace=self.namespace, username=self.username)

    @property
    def formatted_filters(self):
        """
        Cache and return filters as a comprehensive WQL clause.
        """
        if not self._formatted_filters:
            filters = deepcopy(self.filters)
            self._formatted_filters = self._format_filter(filters, self._and_props)
        return self._formatted_filters

    def reset_filter(self, new_filters):
        self.filters = new_filters
        # get rid of the formatted filters so they'll be recalculated
        self._formatted_filters = None

    def sample(self):
        """
        Compute new samples.
        """
        self._sampling = True
        self._runSampleEvent.set()
        while not self._sampleCompleteEvent.wait(timeout=float(self._timeout_duration)):
            if not self._sampler_thread.is_alive():
                raise Exception("The sampler thread terminated unexpectedly")
        self._sampleCompleteEvent.clear()
        self._sampling = False

    def __len__(self):
        """
        Return the number of WMI Objects in the current sample.
        """
        # No data is returned while sampling
        if self._sampling:
            raise TypeError(u"Sampling `WMISampler` object has no len()")

        return len(self._current_sample)

    def __iter__(self):
        """
        Iterate on the current sample's WMI Objects and format the property values.
        """
        # No data is returned while sampling
        if self._sampling:
            raise TypeError(u"Sampling `WMISampler` object is not iterable")

        if self.is_raw_perf_class:
            # Format required
            for previous_wmi_object, current_wmi_object in zip(self._previous_sample, self._current_sample):
                formatted_wmi_object = self._format_property_values(previous_wmi_object, current_wmi_object)
                yield formatted_wmi_object
        else:
            #  No format required
            for wmi_object in self._current_sample:
                yield wmi_object

    def __getitem__(self, index):
        """
        Get the specified formatted WMI Object from the current sample.
        """
        if self.is_raw_perf_class:
            previous_wmi_object = self._previous_sample[index]
            current_wmi_object = self._current_sample[index]
            formatted_wmi_object = self._format_property_values(previous_wmi_object, current_wmi_object)
            return formatted_wmi_object
        else:
            return self._current_sample[index]

    def __eq__(self, other):
        """
        Equality operator is based on the current sample.
        """
        return self._current_sample == other

    def __str__(self):
        """
        Stringify the current sample's WMI Objects.
        """
        return str(self._current_sample)

    def _get_property_calculator(self, counter_type):
        """
        Return the calculator for the given `counter_type`.
        Fallback with `get_raw`.
        """
        calculator = get_raw
        try:
            calculator = get_calculator(counter_type)
        except UndefinedCalculator:
            self.logger.warning(
                u"Undefined WMI calculator for counter_type %s. Values are reported as RAW.", counter_type
            )

        return calculator

    def _format_property_values(self, previous, current):
        """
        Format WMI Object's RAW data based on the previous sample.

        Do not override the original WMI Object !
        """
        formatted_wmi_object = CaseInsensitiveDict()

        for property_name, property_raw_value in iteritems(current):
            counter_type = self._property_counter_types.get(property_name)
            property_formatted_value = property_raw_value

            if counter_type:
                calculator = self._get_property_calculator(counter_type)
                property_formatted_value = calculator(previous, current, property_name)

            formatted_wmi_object[property_name] = property_formatted_value

        return formatted_wmi_object

    def get_connection(self):
        """
        Create a new WMI connection
        """
        self.logger.debug(
            u"Connecting to WMI server (host=%s, namespace=%s, provider=%s, username=%s).",
            self.host,
            self.namespace,
            self.provider,
            self.username,
        )

        additional_args = []

        if self.provider != ProviderArchitecture.DEFAULT:
            context = Dispatch("WbemScripting.SWbemNamedValueSet")
            context.Add("__ProviderArchitecture", self.provider)
            additional_args = [None, "", 128, context]

        locator = Dispatch("WbemScripting.SWbemLocator")
        connection = locator.ConnectServer(self.host, self.namespace, self.username, self.password, *additional_args)

        return connection

    @staticmethod
    def _format_filter(filters, and_props=[]):
        """
        Transform filters to a comprehensive WQL `WHERE` clause.

        In the resulting `WHERE` clause:
         * Specifying multiple filters defaults to an `OR` bool operator.
            E.g.  - foo: x
                  - bar: x
                  result> foo OR bar
         * Specifying multiple properties in a given filter defaults to an `AND` bool operator.
            E.g.  - foo: x
                    bar: x
                  result> foo AND bar
         * Specifying multiple conditions for a given property defaults to an `OR` bool operator unless specified otherwise.
            E.g.  - foo: [x, y, z]
                  result> foo = x OR  y OR  z
                  - bar: {AND: [x, y, z]}
                  result> foo = x AND y AND z

        Builds filter from a filter list.
        - filters: expects a list of dicts, typically:
                - [{'Property': value},...] or
                - [{'Property': [WQL_OP, value]},...] or
                - [{'Property': {BOOL_OP: [WQL_OP, value]},...}]

                NOTE: If we just provide a value we default to '=' WQL operator.
                Otherwise, specify the operator in a list as above: [WQL_OP, value]
                If we detect a wildcard character ('%') we will override the WQL operator
                to use LIKE
        """

        # https://docs.microsoft.com/en-us/windows/win32/wmisdk/wql-operators
        # Not supported: ISA, IS and IS NOT
        # Supported WQL operators.
        WQL_OPERATORS = ('=', '<', '>', '<=', '>=', '!=', '<>', 'LIKE')

        # Supported bool operators
        # Also takes NOT which maps to NAND or NOR depending on default_bool_op
        BOOL_OPERATORS = ('AND', 'OR', 'NAND', 'NOR')

        def build_where_clause(fltr):
            def add_to_bool_ops(k, v):
                if isinstance(v, (tuple, list)):
                    if len(v) == 2 and isinstance(v[0], string_types) and v[0].upper() in WQL_OPERATORS:
                        # Append if: [WQL_OP, value]
                        #     PROPERTY: ['<WQL_OP>', '%bar']
                        #     PROPERTY: { <BOOL_OP>: ['<WQL_OP>', 'foo']}
                        bool_ops[k].append(v)
                    else:
                        # Extend if: list of string value/s, or list of [WQL_OP, value]
                        #     PROPERTY: [foo%]
                        #     PROPERTY: [['<WQL_OP>', '%bar']]
                        #     PROPERTY: ['foo%', '%bar']
                        #     PROPERTY: { <BOOL_OP>: [['<WQL_OP>', 'foo']]}
                        #     PROPERTY: { <BOOL_OP>: ['foo%', '%bar']]}
                        bool_ops[k].extend(v)
                else:
                    # Append if: string value
                    #     PROPERTY: foo%
                    #     PROPERTY: { <BOOL_OP>: foo%]}
                    bool_ops[k].append(v)

            f = fltr.pop()
            wql = ""
            while f:
                bool_ops = dict((op, []) for op in BOOL_OPERATORS)
                default_bool_op = 'OR'
                default_wql_op = '='
                clauses = []
                prop, value = f.popitem()
                for p in and_props:
                    if p.lower() in prop.lower():
                        default_bool_op = 'AND'
                        break

                if isinstance(value, (tuple, list)):
                    # e.g.
                    # PROPERTY: [WQL_OP, val]
                    # PROPERTY: [foo, bar]
                    add_to_bool_ops(default_bool_op, value)
                elif isinstance(value, dict):
                    # e.g.
                    # PROPERTY:
                    #   BOOL_OP:
                    #     - [WQL_OP, val]
                    #     - foo
                    #     - bar
                    for k, v in iteritems(value):
                        bool_op = default_bool_op
                        if k.upper() in BOOL_OPERATORS:
                            bool_op = k.upper()
                        elif k.upper() == 'NOT':
                            # map NOT to NOR or NAND
                            bool_op = 'N{}'.format(default_bool_op)
                        add_to_bool_ops(bool_op, v)
                elif isinstance(value, string_types) and '%' in value:
                    # Override operator to LIKE if wildcard detected
                    # e.g.
                    # PROPERTY: 'foo%'  -> PROPERTY LIKE 'foo%'
                    add_to_bool_ops(default_bool_op, ['LIKE', value])
                else:
                    # Use default comparison operator
                    # e.g.
                    # PROPERTY: 'bar'   -> PROPERTY = 'foo'
                    add_to_bool_ops(default_bool_op, [default_wql_op, value])

                for bool_op, value in iteritems(bool_ops):
                    if not len(value):
                        continue

                    internal_filter = map(
                        lambda x: (prop, x)
                        if isinstance(x, (tuple, list))
                        else (prop, ('LIKE', x))
                        if isinstance(x, string_types) and '%' in x
                        else (prop, (default_wql_op, x)),
                        value,
                    )

                    negate = True if bool_op.upper() in ('NAND', 'NOR') else False
                    op = ' {} '.format(bool_op[1:] if negate else bool_op)
                    clause = op.join(
                        [
                            '{0} {1} \'{2}\''.format(k, v[0] if v[0].upper() in WQL_OPERATORS else default_wql_op, v[1])
                            for k, v in internal_filter
                        ]
                    )

                    if negate:
                        clauses.append("NOT ( {clause} )".format(clause=clause))
                    elif len(value) > 1:
                        clauses.append("( {clause} )".format(clause=clause))
                    else:
                        clauses.append("{clause}".format(clause=clause))

                wql += ' {} '.format(default_bool_op).join(clauses)
                if f:
                    wql += " AND "

            # empty list skipped
            if wql.endswith(" AND "):
                wql = wql[:-5]

            if len(fltr) == 0:
                return "( {clause} )".format(clause=wql)

            return "( {clause} ) OR {more}".format(clause=wql, more=build_where_clause(fltr))

        if not filters:
            return ""

        return " WHERE {clause}".format(clause=build_where_clause(filters))

    def _query(self):  # pylint: disable=E0202
        """
        Query WMI using WMI Query Language (WQL) & parse the results.

        Returns: List of WMI objects or `TimeoutException`.
        """
        try:
            formated_property_names = ",".join(self.property_names)
            wql = "Select {property_names} from {class_name}{filters}".format(
                property_names=formated_property_names, class_name=self.class_name, filters=self.formatted_filters
            )
            self.logger.debug(u"Querying WMI: %s", wql)
        except Exception as e:
            self.logger.error(str(e))
            return []

        try:
            # From: https://msdn.microsoft.com/en-us/library/aa393866(v=vs.85).aspx
            flag_return_immediately = 0x10  # Default flag.
            flag_forward_only = 0x20
            flag_use_amended_qualifiers = 0x20000

            query_flags = flag_return_immediately | flag_forward_only

            # For the first query, cache the qualifiers to determine each
            # propertie's "CounterType"
            includes_qualifiers = self.is_raw_perf_class and self._property_counter_types is None
            if includes_qualifiers:
                self._property_counter_types = CaseInsensitiveDict()
                query_flags |= flag_use_amended_qualifiers

            raw_results = self.get_connection().ExecQuery(wql, "WQL", query_flags)

            results = self._parse_results(raw_results, includes_qualifiers=includes_qualifiers)

        except pywintypes.com_error:
            self.logger.warning(u"Failed to execute WMI query (%s)", wql, exc_info=True)
            results = []

        return results

    def _parse_results(self, raw_results, includes_qualifiers):
        """
        Parse WMI query results in a more comprehensive form.

        Returns: List of WMI objects
        ```
        [
            {
                'freemegabytes': 19742.0,
                'name': 'C:',
                'avgdiskbytesperwrite': 1536.0
            }, {
                'freemegabytes': 19742.0,
                'name': 'D:',
                'avgdiskbytesperwrite': 1536.0
            }
        ]
        ```
        """
        results = []
        for res in raw_results:
            # Ensure all properties are available. Use case-insensitivity
            # because some properties are returned with different cases.
            item = CaseInsensitiveDict()
            for prop_name in self.property_names:
                item[prop_name] = None

            for wmi_property in res.Properties_:
                # IMPORTANT: To improve performance, only access the Qualifiers
                # if the "CounterType" hasn't already been cached.
                should_get_qualifier_type = (
                    includes_qualifiers and wmi_property.Name not in self._property_counter_types
                )

                if should_get_qualifier_type:

                    # Can't index into "Qualifiers_" for keys that don't exist
                    # without getting an exception.
                    qualifiers = dict((q.Name, q.Value) for q in wmi_property.Qualifiers_)

                    # Some properties like "Name" and "Timestamp_Sys100NS" do
                    # not have a "CounterType" (since they're not a counter).
                    # Therefore, they're ignored.
                    if "CounterType" in qualifiers:
                        counter_type = qualifiers["CounterType"]
                        self._property_counter_types[wmi_property.Name] = counter_type

                        self.logger.debug(
                            u"Caching property qualifier CounterType: %s.%s = %s",
                            self.class_name,
                            wmi_property.Name,
                            counter_type,
                        )
                    else:
                        self.logger.debug(
                            u"CounterType qualifier not found for %s.%s", self.class_name, wmi_property.Name
                        )

                try:
                    item[wmi_property.Name] = float(wmi_property.Value)
                except (TypeError, ValueError):
                    item[wmi_property.Name] = wmi_property.Value

            results.append(item)
        return results
