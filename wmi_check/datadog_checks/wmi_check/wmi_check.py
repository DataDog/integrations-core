# (C) Datadog, Inc. 2013-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from datadog_checks.checks.win.wmi import WinWMICheck
from datadog_checks.utils.containers import hash_mutable
from datadog_checks.utils.timeout import TimeoutException


class WMICheck(WinWMICheck):
    """
    WMI check.

    Windows only.
    """

    def __init__(self, name, init_config, agentConfig, instances):
        WinWMICheck.__init__(self, name, init_config, agentConfig, instances)
        self.wmi_samplers = {}
        self.wmi_props = {}

    def check(self, instance):
        """
        Fetch WMI metrics.
        """

        # Connection information
        host = instance.get('host', "localhost")
        namespace = instance.get('namespace', "root\\cimv2")
        provider = instance.get('provider')
        username = instance.get('username', "")
        password = instance.get('password', "")

        # WMI instance
        wmi_class = instance.get('class')
        metrics = instance.get('metrics')
        filters = instance.get('filters')
        tag_by = instance.get('tag_by', "")
        tag_queries = instance.get('tag_queries', [])

        constant_tags = instance.get('constant_tags')
        custom_tags = instance.get('tags', [])
        if constant_tags is None:
            constant_tags = list(custom_tags)
        else:
            constant_tags.extend(custom_tags)
            self.log.warning("`constant_tags` is being deprecated, please use `tags`")

        # Create or retrieve an existing WMISampler
        instance_hash = hash_mutable(instance)
        instance_key = self._get_instance_key(host, namespace, wmi_class, instance_hash)

        metric_name_and_type_by_property, properties = self._get_wmi_properties(instance_key, metrics, tag_queries)

        wmi_sampler = self._get_running_wmi_sampler(
            instance_key,
            wmi_class,
            properties,
            tag_by=tag_by,
            filters=filters,
            host=host,
            namespace=namespace,
            provider=provider,
            username=username,
            password=password,
        )

        # Sample, extract & submit metrics
        try:
            wmi_sampler.sample()
            metrics = self._extract_metrics(wmi_sampler, tag_by, tag_queries, constant_tags)
        except TimeoutException:
            self.log.warning(
                "WMI query timed out. class=%s - properties=%s - filters=%s - tag_queries=%s",
                wmi_class,
                properties,
                filters,
                tag_queries,
            )
        else:
            self._submit_metrics(metrics, metric_name_and_type_by_property)
