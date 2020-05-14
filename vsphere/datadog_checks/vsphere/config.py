import re
from typing import List

from pyVmomi import vim
from six import iteritems, string_types

from datadog_checks.base import ConfigurationError, is_affirmative
from datadog_checks.base.log import CheckLoggingAdapter
from datadog_checks.vsphere.constants import (
    ALLOWED_FILTER_PROPERTIES,
    ALLOWED_FILTER_TYPES,
    DEFAULT_BATCH_COLLECTOR_SIZE,
    DEFAULT_MAX_QUERY_METRICS,
    DEFAULT_METRICS_PER_QUERY,
    DEFAULT_REFRESH_INFRASTRUCTURE_CACHE_INTERVAL,
    DEFAULT_REFRESH_METRICS_METADATA_CACHE_INTERVAL,
    DEFAULT_TAGS_COLLECTOR_SIZE,
    DEFAULT_THREAD_COUNT,
    DEFAULT_VSPHERE_TAG_PREFIX,
    EXTRA_FILTER_PROPERTIES_FOR_VMS,
    HISTORICAL_RESOURCES,
    MOR_TYPE_AS_STRING,
    REALTIME_RESOURCES,
)
from datadog_checks.vsphere.resource_filters import ResourceFilter, create_resource_filter
from datadog_checks.vsphere.types import InstanceConfig, MetricFilterConfig, MetricFilters, ResourceFilterConfig


class VSphereConfig(object):
    def __init__(self, instance, log):
        # type: (InstanceConfig, CheckLoggingAdapter) -> None
        self.log = log

        # Connection parameters
        self.hostname = instance['host']
        self.username = instance['username']
        self.password = instance['password']
        self.ssl_verify = is_affirmative(instance.get('ssl_verify', True))
        self.ssl_capath = instance.get('ssl_capath')
        self.tls_ignore_warning = instance.get('tls_ignore_warning', False)

        # vSphere options
        self.collection_level = instance.get("collection_level", 1)
        self.collection_type = instance.get("collection_type", "realtime")
        self.use_guest_hostname = instance.get("use_guest_hostname", False)
        self.max_historical_metrics = instance.get("max_historical_metrics", DEFAULT_MAX_QUERY_METRICS)

        # Check option
        self.threads_count = instance.get("threads_count", DEFAULT_THREAD_COUNT)
        self.metrics_per_query = instance.get("metrics_per_query", DEFAULT_METRICS_PER_QUERY)
        self.batch_collector_size = instance.get('batch_property_collector_size', DEFAULT_BATCH_COLLECTOR_SIZE)
        self.batch_tags_collector_size = instance.get('batch_tags_collector_size', DEFAULT_TAGS_COLLECTOR_SIZE)
        self.should_collect_events = instance.get("collect_events", self.collection_type == 'realtime')
        self.should_collect_tags = is_affirmative(instance.get("collect_tags", False))
        self.tags_prefix = instance.get("tags_prefix", DEFAULT_VSPHERE_TAG_PREFIX)
        self.excluded_host_tags = instance.get("excluded_host_tags", [])
        self.base_tags = instance.get("tags", []) + ["vcenter_server:{}".format(self.hostname)]
        self.refresh_infrastructure_cache_interval = instance.get(
            'refresh_infrastructure_cache_interval', DEFAULT_REFRESH_INFRASTRUCTURE_CACHE_INTERVAL
        )
        self.refresh_metrics_metadata_cache_interval = instance.get(
            'refresh_metrics_metadata_cache_interval', DEFAULT_REFRESH_METRICS_METADATA_CACHE_INTERVAL
        )

        # Utility
        if self.collection_type == 'both':
            self.collected_resource_types = REALTIME_RESOURCES + HISTORICAL_RESOURCES
        elif self.collection_type == 'historical':
            self.collected_resource_types = HISTORICAL_RESOURCES
        else:
            self.collected_resource_types = REALTIME_RESOURCES

        # Filters
        self.resource_filters = self._parse_resource_filters(instance.get("resource_filters", []))
        self.metric_filters = self._parse_metric_regex_filters(instance.get("metric_filters", {}))
        # Since `collect_per_instance_filters` have the same structure as `metric_filters` we use the same parser
        self.collect_per_instance_filters = self._parse_metric_regex_filters(
            instance.get("collect_per_instance_filters", {})
        )

        self.validate_config()

    def is_historical(self):
        # type: () -> bool
        return self.collection_type in ('historical', 'both')

    def validate_config(self):
        # type: () -> None
        if not self.ssl_verify and self.ssl_capath:
            self.log.warning(
                "Your configuration is incorrectly attempting to "
                "specify both a CA path, and to disable SSL "
                "verification. You cannot do both. Proceeding with "
                "disabling ssl verification."
            )

        if self.collection_type not in ('realtime', 'historical', 'both'):
            raise ConfigurationError(
                "Your configuration is incorrectly attempting to "
                "set the `collection_type` to {}. It should be either "
                "'realtime', 'historical' or 'both'.".format(self.collection_type)
            )

        if self.collection_level not in (1, 2, 3, 4):
            raise ConfigurationError(
                "Your configuration is incorrectly attempting to "
                "set the collection_level to something different than a "
                "integer between 1 and 4."
            )

        if not self.should_collect_tags:
            for resource_filter in self.resource_filters:
                if resource_filter.property_name == 'tag':
                    raise ConfigurationError(
                        'Your configuration is incorrectly attempting to filter resources '
                        'by the `tag` property but `collect_tags` is disabled.'
                    )

    def _parse_resource_filters(self, all_resource_filters):
        # type: (List[ResourceFilterConfig]) -> List[ResourceFilter]

        # Keep a list of resource filters ids (tuple of resource, property and type) that are already registered.
        # This is to prevent users to define the same filter twice with different patterns.
        resource_filters_ids = []
        formatted_resource_filters = []  # type: List[ResourceFilter]
        allowed_resource_types = [MOR_TYPE_AS_STRING[k] for k in self.collected_resource_types]

        for resource_filter in all_resource_filters:
            # Optional fields:
            if 'type' not in resource_filter:
                resource_filter['type'] = 'whitelist'
            if 'property' not in resource_filter:
                resource_filter['property'] = 'name'

            # Check required fields and their types
            for (field, field_type) in iteritems(
                {'resource': string_types, 'property': string_types, 'type': string_types, 'patterns': list}
            ):
                if field not in resource_filter:
                    self.log.warning(
                        "Ignoring filter %r because it doesn't contain a %s field.", resource_filter, field
                    )
                    continue
                if not isinstance(resource_filter[field], field_type):  # type: ignore
                    self.log.warning(
                        "Ignoring filter %r because field %s should have type %s.", resource_filter, field, field_type
                    )
                    continue

            # Check `resource` validity
            if resource_filter['resource'] not in allowed_resource_types:
                self.log.warning(
                    "Ignoring filter %r because resource %s is not collected when collection_type is %s.",
                    resource_filter,
                    resource_filter['resource'],
                    self.collection_type,
                )
                continue

            # Check `property` validity
            allowed_prop_names = ALLOWED_FILTER_PROPERTIES
            if resource_filter['resource'] == MOR_TYPE_AS_STRING[vim.VirtualMachine]:
                allowed_prop_names += EXTRA_FILTER_PROPERTIES_FOR_VMS

            if resource_filter['property'] not in allowed_prop_names:
                self.log.warning(
                    "Ignoring filter %r because property '%s' is not valid "
                    "for resource type %s. Should be one of %r.",
                    resource_filter,
                    resource_filter['property'],
                    resource_filter['resource'],
                    allowed_prop_names,
                )
                continue

            # Check `type` validity
            if resource_filter['type'] not in ALLOWED_FILTER_TYPES:
                self.log.warning(
                    "Ignoring filter %r because type '%s' is not valid. Should be one of %r.",
                    resource_filter,
                    resource_filter['type'],
                    ALLOWED_FILTER_TYPES,
                )
            patterns = [re.compile(r) for r in resource_filter['patterns']]
            filter_instance = create_resource_filter(
                resource_filter['resource'],
                resource_filter['property'],
                patterns,
                is_whitelist=(resource_filter['type'] == 'whitelist'),
            )
            if filter_instance.unique_key() in resource_filters_ids:
                self.log.warning(
                    "Ignoring filter %r because you already have a `%s` filter for resource type %s and property %s.",
                    resource_filter,
                    resource_filter['type'],
                    resource_filter['resource'],
                    resource_filter['property'],
                )
                continue

            formatted_resource_filters.append(filter_instance)
            resource_filters_ids.append(filter_instance.unique_key())

        return formatted_resource_filters

    def _parse_metric_regex_filters(self, all_metric_filters):
        # type: (MetricFilterConfig) -> MetricFilters
        allowed_resource_types = [MOR_TYPE_AS_STRING[k] for k in self.collected_resource_types]
        metric_filters = {}
        for resource_type, filters in iteritems(all_metric_filters):
            if resource_type not in allowed_resource_types:
                self.log.warning(
                    "Ignoring metric_filter for resource '%s'. When collection_type is '%s', it should be one of '%s'",
                    resource_type,
                    self.collection_type,
                    ",".join(allowed_resource_types),
                )
                continue
            metric_filters[resource_type] = filters

        return {k: [re.compile(r) for r in v] for k, v in iteritems(metric_filters)}
