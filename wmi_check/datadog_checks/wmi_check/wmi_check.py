# (C) Datadog, Inc. 2013-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from typing import Any, Dict, List

from datadog_checks.base.checks.win.wmi import WinWMICheck
from datadog_checks.base.checks.win.wmi.types import TagQuery, WMIFilter, WMIMetric, WMIProperties
from datadog_checks.base.errors import CheckException
from datadog_checks.base.utils.timeout import TimeoutException


class WMICheck(WinWMICheck):
    """
    WMI check.

    Windows only.
    """

    def __init__(self, name, init_config, instances):
        # type: (str, Dict[str, Any], List[Dict[str, Any]]) -> None
        super(WMICheck, self).__init__(name, init_config, instances)
        self.custom_tags = self.instance.get('tags', [])  # type: List[str]
        self.filters = self.instance.get('filters', [])  # type: List[Dict[str, WMIFilter]]
        self.metrics_to_capture = self.instance.get('metrics', [])  # type: List[List[str]]
        self.tag_by = self.instance.get('tag_by', "")  # type: str
        self.tag_queries = self.instance.get('tag_queries', [])  # type: List[TagQuery]

    def check(self, _):
        # type: (Any) -> None
        """
        Fetch WMI metrics.
        """
        constant_tags = self.instance.get('constant_tags', [])
        if constant_tags:
            self.log.warning("`constant_tags` is being deprecated, please use `tags`")
        constant_tags.extend(self.custom_tags)

        # Create or retrieve an existing WMISampler
        metric_name_and_type_by_property, properties = self.get_wmi_properties()

        wmi_sampler = self.get_running_wmi_sampler(properties, self.filters)

        # Sample, extract & submit metrics
        try:
            wmi_sampler.sample()
            extracted_metrics = self.extract_metrics(constant_tags=constant_tags)
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

    def extract_metrics(self, constant_tags):
        # type: (List[str]) -> List[WMIMetric]
        if not self._wmi_sampler:
            raise CheckException("A running sampler is needed before you can extract metrics")
        return self._extract_metrics(self._wmi_sampler, self.tag_by, self.tag_queries, constant_tags)

    def get_wmi_properties(self):
        # type: () -> WMIProperties
        return self._get_wmi_properties(None, self.metrics_to_capture, self.tag_queries)
