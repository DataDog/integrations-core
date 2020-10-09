# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict, List, Optional, Tuple

from six import iteritems

from ... import AgentCheck
from .sampler import WMISampler
from .types import TagQuery, WMIFilter, WMIMetric, WMIObject, WMIProperties


class InvalidWMIQuery(Exception):
    """
    Invalid WMI Query.
    """

    pass


class MissingTagBy(Exception):
    """
    WMI query returned multiple rows but no `tag_by` value was given.
    """

    pass


class TagQueryUniquenessFailure(Exception):
    """
    'Tagging query' did not return or returned multiple results.
    """

    pass


class WinWMICheck(AgentCheck):
    """
    WMI check.

    Windows only.
    """

    def __init__(self, *args, **kwargs):  # To support optional agentConfig
        # type: (*Any, **Any) -> None
        super(WinWMICheck, self).__init__(*args, **kwargs)

        # Connection information
        self.host = self.instance.get('host', "localhost")  # type: str
        self.namespace = self.instance.get('namespace', "root\\cimv2")  # type: str
        self.provider = self.instance.get('provider')  # type: Optional[int]
        self.username = self.instance.get('username', "")  # type: str
        self.password = self.instance.get('password', "")  # type: str

        # WMI instance
        self.wmi_class = self.instance.get('class', '')  # type: str

        self._wmi_sampler = None  # type: Optional[WMISampler]
        self._wmi_props = None  # type: Optional[WMIProperties]

    def _format_tag_query(self, sampler, wmi_obj, tag_query):
        # type: (WMISampler, WMIObject, TagQuery) -> Tuple[str, str, List[Dict]]
        """
        Format `tag_query` or raise on incorrect parameters.
        """
        try:
            link_source_property = int(wmi_obj[tag_query[0]])
            target_class = tag_query[1]
            link_target_class_property = tag_query[2]
            target_property = tag_query[3]
        except IndexError:
            self.log.error(
                u"Wrong `tag_queries` parameter format. " "Please refer to the configuration file for more information."
            )
            raise
        except TypeError:
            wmi_property = tag_query[0]
            wmi_class = sampler.class_name
            self.log.error(
                u"Incorrect 'link source property' in `tag_queries` parameter: `%s` is not a property of `%s`",
                wmi_property,
                wmi_class,
            )
            raise

        return target_class, target_property, [{link_target_class_property: link_source_property}]

    def _raise_on_invalid_tag_query_result(self, sampler, wmi_obj, tag_query):
        # type: (WMISampler, WMIObject, TagQuery) -> None
        target_property = sampler.property_names[0]
        target_class = sampler.class_name

        if len(sampler) != 1:
            message = "no result was returned"
            if len(sampler):
                message = "multiple results returned (one expected)"

            self.log.warning(
                u"Failed to extract a tag from `tag_queries` parameter: %s. wmi_object=%s - query=%s",
                message,
                wmi_obj,
                tag_query,
            )
            raise TagQueryUniquenessFailure

        if sampler[0][target_property] is None:
            self.log.error(
                u"Incorrect 'target property' in `tag_queries` parameter: `%s` is empty or is not a property of `%s`",
                target_property,
                target_class,
            )
            raise TypeError

    def _get_tag_query_tag(self, sampler, wmi_obj, tag_query):
        # type: (WMISampler, WMIObject, TagQuery) -> str
        """
        Design a query based on the given WMIObject to extract a tag.

        Returns: tag or TagQueryUniquenessFailure exception.
        """
        self.log.debug(u"`tag_queries` parameter found. wmi_object=%s - query=%s", wmi_obj, tag_query)

        # Extract query information
        target_class, target_property, filters = self._format_tag_query(sampler, wmi_obj, tag_query)

        # Create a specific sampler
        with WMISampler(
            self.log, target_class, [target_property], filters=filters, **sampler.connection
        ) as tag_query_sampler:
            tag_query_sampler.sample()

            # Extract tag
            self._raise_on_invalid_tag_query_result(tag_query_sampler, wmi_obj, tag_query)

            link_value = str(tag_query_sampler[0][target_property]).lower()

        tag = "{tag_name}:{tag_value}".format(tag_name=target_property.lower(), tag_value="_".join(link_value.split()))

        self.log.debug(u"Extracted `tag_queries` tag: '%s'", tag)
        return tag

    def _extract_metrics(self, wmi_sampler, tag_by, tag_queries, constant_tags):
        # type: (WMISampler, str, List[List[str]], List[str]) -> List[WMIMetric]
        """
        Extract and tag metrics from the WMISampler.

        Raise when multiple WMIObject were returned by the sampler with no `tag_by` specified.

        Returns: List of WMIMetric
        ```
        [
            WMIMetric("freemegabytes", 19742, ["name:_total"]),
            WMIMetric("avgdiskbytesperwrite", 1536, ["name:c:"]),
        ]
        ```
        """
        if len(wmi_sampler) > 1 and not tag_by:
            raise MissingTagBy(
                u"WMI query returned multiple rows but no `tag_by` value was given."
                " class={wmi_class} - properties={wmi_properties} - filters={filters}".format(
                    wmi_class=wmi_sampler.class_name,
                    wmi_properties=wmi_sampler.property_names,
                    filters=wmi_sampler.filters,
                )
            )

        extracted_metrics = []
        tag_by = tag_by.lower()

        for wmi_obj in wmi_sampler:
            tags = list(constant_tags) if constant_tags else []

            # Tag with `tag_queries` parameter
            for query in tag_queries:
                try:
                    tags.append(self._get_tag_query_tag(wmi_sampler, wmi_obj, query))
                except TagQueryUniquenessFailure:
                    continue

            for wmi_property, wmi_value in iteritems(wmi_obj):
                # skips any property not in arguments since SWbemServices.ExecQuery will return key prop properties
                # https://msdn.microsoft.com/en-us/library/aa393866(v=vs.85).aspx

                # skip wmi_property "foo,bar"; there will be a separate wmi_property for each "foo" and "bar"
                if ',' in wmi_property:
                    continue

                normalized_wmi_property = wmi_property.lower()
                for s in wmi_sampler.property_names:
                    if normalized_wmi_property in s.lower():
                        # wmi_property: "foo" should be found in property_names ["foo,bar", "name"]
                        break
                else:
                    continue
                # Tag with `tag_by` parameter
                for t in tag_by.split(','):
                    t = t.strip()
                    if wmi_property == t:
                        tag_value = str(wmi_value).lower()
                        if tag_queries and tag_value.find("#") > 0:
                            tag_value = tag_value[: tag_value.find("#")]

                        tags.append("{name}:{value}".format(name=t, value=tag_value))
                        continue

                # No metric extraction on 'Name' and properties in tag_by
                if wmi_property == 'name' or normalized_wmi_property in tag_by.lower():
                    continue

                try:
                    extracted_metrics.append(WMIMetric(wmi_property, float(wmi_value), tags))
                except ValueError:
                    self.log.warning(
                        u"When extracting metrics with WMI, found a non digit value for property '%s'.", wmi_property
                    )
                    continue
                except TypeError:
                    self.log.warning(u"When extracting metrics with WMI, found a missing property '%s'", wmi_property)
                    continue
        return extracted_metrics

    def _submit_metrics(self, metrics, metric_name_and_type_by_property):
        # type: (List[WMIMetric], Dict[str, Tuple[str, str]]) -> None
        """
        Resolve metric names and types and submit it.
        """
        for metric in metrics:
            if (
                metric.name not in metric_name_and_type_by_property
                and metric.name.lower() not in metric_name_and_type_by_property
            ):
                # Only report the metrics that were specified in the configuration
                # Ignore added properties like 'Timestamp_Sys100NS', `Frequency_Sys100NS`, etc ...
                continue

            if metric_name_and_type_by_property.get(metric.name):
                metric_name, metric_type = metric_name_and_type_by_property[metric.name]
            elif metric_name_and_type_by_property.get(metric.name.lower()):
                metric_name, metric_type = metric_name_and_type_by_property[metric.name.lower()]
            else:
                continue

            try:
                func = getattr(self, metric_type.lower())
            except AttributeError:
                raise Exception(u"Invalid metric type: {0}".format(metric_type))

            func(metric_name, metric.value, metric.tags)

    def _get_instance_key(self, host, namespace, wmi_class, other=None):
        # type: (str, str, str, Any) -> str
        """
        Return an index key for a given instance. Useful for caching.
        """
        if other:
            return "{host}:{namespace}:{wmi_class}-{other}".format(
                host=host, namespace=namespace, wmi_class=wmi_class, other=other
            )
        return "{host}:{namespace}:{wmi_class}".format(host=host, namespace=namespace, wmi_class=wmi_class)

    def get_running_wmi_sampler(self, properties, filters, **kwargs):
        # type: (List[str], List[Dict[str, WMIFilter]], **Any) -> WMISampler
        tag_by = kwargs.pop('tag_by', "")
        return self._get_running_wmi_sampler(
            instance_key=None,
            wmi_class=self.wmi_class,
            properties=properties,
            filters=filters,
            host=self.host,
            namespace=self.namespace,
            provider=self.provider,
            username=self.username,
            password=self.password,
            tag_by=tag_by,
            **kwargs
        )

    def _get_running_wmi_sampler(self, instance_key, wmi_class, properties, tag_by="", **kwargs):
        # type: (Any, str, List[str], str, Any) -> WMISampler
        """
        Return a running WMISampler for the given (class, properties).

        If no matching WMISampler is running yet, start one and cache it.
        """
        if self._wmi_sampler is None:
            property_list = list(properties) + [tag_by] if tag_by else list(properties)
            self._wmi_sampler = WMISampler(self.log, wmi_class, property_list, **kwargs)
            self._wmi_sampler.start()

        return self._wmi_sampler

    def _get_wmi_properties(self, instance_key, metrics, tag_queries):
        # type: (Any, List[List[str]], List[List[str]]) -> WMIProperties
        """
        Create and cache a (metric name, metric type) by WMI property map and a property list.
        """
        if not self._wmi_props:
            metric_name_by_property = dict(
                (wmi_property.lower(), (metric_name, metric_type)) for wmi_property, metric_name, metric_type in metrics
            )  # type: Dict[str, Tuple[str, str]]
            properties = map(lambda x: x[0], metrics + tag_queries)  # type: List[str]

            self._wmi_props = (metric_name_by_property, properties)

        return self._wmi_props


def from_time(
    year=None, month=None, day=None, hours=None, minutes=None, seconds=None, microseconds=None, timezone=None
):
    # type: (int, int, int, int, int, int, int, int) -> str
    """Convenience wrapper to take a series of date/time elements and return a WMI time
    of the form `yyyymmddHHMMSS.mmmmmm+UUU`. All elements may be int, string or
    omitted altogether. If omitted, they will be replaced in the output string
    by a series of stars of the appropriate length.
    :param year: The year element of the date/time
    :param month: The month element of the date/time
    :param day: The day element of the date/time
    :param hours: The hours element of the date/time
    :param minutes: The minutes element of the date/time
    :param seconds: The seconds element of the date/time
    :param microseconds: The microseconds element of the date/time
    :param timezone: The timezone element of the date/time
    :returns: A WMI datetime string of the form: `yyyymmddHHMMSS.mmmmmm+UUU`
    """

    def str_or_stars(i, length):
        # type: (Optional[int], int) -> str
        if i is None:
            return "*" * length
        else:
            return str(i).rjust(length, "0")

    wmi_time = ""
    wmi_time += str_or_stars(year, 4)
    wmi_time += str_or_stars(month, 2)
    wmi_time += str_or_stars(day, 2)
    wmi_time += str_or_stars(hours, 2)
    wmi_time += str_or_stars(minutes, 2)
    wmi_time += str_or_stars(seconds, 2)
    wmi_time += "."
    wmi_time += str_or_stars(microseconds, 6)
    if timezone is None:
        wmi_time += "+"
    else:
        try:
            int(timezone)
        except ValueError:
            wmi_time += "+"
        else:
            if timezone >= 0:
                wmi_time += "+"
            else:
                wmi_time += "-"
                timezone = abs(timezone)
                wmi_time += str_or_stars(timezone, 3)

    return wmi_time


def to_time(wmi_time):
    # type: (str) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int], Optional[int], Optional[int], Optional[int], Optional[str]]
    """Convenience wrapper to take a WMI datetime string of the form
    yyyymmddHHMMSS.mmmmmm+UUU and return a 9-tuple containing the
    individual elements, or None where string contains placeholder
    stars.

    :param wmi_time: The WMI datetime string in `yyyymmddHHMMSS.mmmmmm+UUU` format

    :returns: A 9-tuple of (year, month, day, hours, minutes, seconds, microseconds, timezone)
    """

    def int_or_none(s, start, end):
        # type: (str, int, int) -> Optional[int]
        try:
            return int(s[start:end])
        except ValueError:
            return None

    year = int_or_none(wmi_time, 0, 4)
    month = int_or_none(wmi_time, 4, 6)
    day = int_or_none(wmi_time, 6, 8)
    hours = int_or_none(wmi_time, 8, 10)
    minutes = int_or_none(wmi_time, 10, 12)
    seconds = int_or_none(wmi_time, 12, 14)
    microseconds = int_or_none(wmi_time, 15, 21)
    timezone = wmi_time[22:]  # type: Optional[str]

    if timezone == "***":
        timezone = None

    return year, month, day, hours, minutes, seconds, microseconds, timezone
