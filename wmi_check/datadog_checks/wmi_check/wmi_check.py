# (C) Datadog, Inc. 2013-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from datadog_checks.base.checks.win.wmi import WinWMICheck
from datadog_checks.base.utils.timeout import TimeoutException


class WMICheck(WinWMICheck):
    """
    WMI check.

    Windows only.
    """

    def __init__(self, name, init_config, instances):
        super(WinWMICheck, self).__init__(name, init_config, instances)
        self.custom_tags = self.instance.get('tags', [])

    def check(self, _):
        """
        Fetch WMI metrics.
        """
        constant_tags = self.instance.get('constant_tags', [])
        if constant_tags:
            self.log.warning("`constant_tags` is being deprecated, please use `tags`")
        constant_tags.extend(self.custom_tags)

        # Create or retrieve an existing WMISampler
        metric_name_and_type_by_property, properties = self.get_wmi_properties()

        wmi_sampler = self.get_running_wmi_sampler(properties)

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
