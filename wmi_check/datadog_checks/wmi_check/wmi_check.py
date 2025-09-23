# (C) Datadog, Inc. 2013-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from typing import Any, Dict, List  # noqa: F401

from datadog_checks.base.checks.win.wmi import WinWMICheck, WMISampler  # noqa: F401
from datadog_checks.base.checks.win.wmi.types import TagQuery, WMIFilter, WMIMetric, WMIProperties  # noqa: F401
from datadog_checks.base.utils.timeout import TimeoutException


class WMICheck(WinWMICheck):
    """
    WMI check.

    Windows only.
    """

    def __init__(self, name, init_config, instances):
        # type: (str, Dict[str, Any], List[Dict[str, Any]]) -> None
        super(WMICheck, self).__init__(name, init_config, instances)
        self.filters = self.instance.get('filters', [])  # type: List[Dict[str, WMIFilter]]
        self.metrics_to_capture = self.instance.get('metrics', [])  # type: List[List[str]]
        self.tag_by = self.instance.get('tag_by', "")  # type: str
        self.tag_queries = self.instance.get('tag_queries', [])  # type: List[TagQuery]

        custom_tags = self.instance.get('tags', [])  # type: List[str]
        self.constant_tags = self.instance.get('constant_tags', [])  # type: List[str]
        if self.constant_tags:
            self.log.warning("`constant_tags` is being deprecated, please use `tags`")
        self.constant_tags.extend(custom_tags)

    def check(self, _):
        # type: (Any) -> None
        """
        Fetch WMI metrics.
        """
        # Create or retrieve an existing WMISampler
        metric_name_and_type_by_property, properties = self.get_wmi_properties()

        wmi_sampler = self.get_running_wmi_sampler(properties, self.filters, tag_by=self.tag_by)

        # Sample, extract & submit metrics
        try:
            wmi_sampler.sample()
            extracted_metrics = self.extract_metrics(wmi_sampler)
        except TimeoutException:
            self.log.warning(
                "WMI query timed out. class=%s - properties=%s - filters=%s - tag_queries=%s",
                self.wmi_class,
                properties,
                self.filters,
                self.tag_queries,
            )
        else:
            self._submit_metrics(extracted_metrics, metric_name_and_type_by_property)

    def extract_metrics(self, wmi_sampler):
        # type: (WMISampler) -> List[WMIMetric]
        return self._extract_metrics(wmi_sampler, self.tag_by, self.tag_queries, self.constant_tags)

    def get_wmi_properties(self):
        # type: () -> WMIProperties
        return self._get_wmi_properties(None, self.metrics_to_capture, self.tag_queries)
