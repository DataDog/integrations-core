# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import re
import ssl
from collections import defaultdict

from pyVim import connect
from pyVmomi import vim, vmodl
from six import iteritems

from datadog_checks.base import AgentCheck, is_affirmative
from datadog_checks.base.utils.common import to_string

from .constants import (
    ALL_RESOURCES,
    ALLOWED_FILTER_PROPERTIES,
    ALLOWED_FILTER_TYPES,
    AVAILABLE_HOST_TAGS,
    EXTRA_FILTER_PROPERTIES_FOR_VMS,
    HOST_RESOURCE,
    MAX_PROPERTIES,
    RESOURCE_TYPE_TO_NAME,
    SHORT_ROLLUP,
    VM_RESOURCE,
)
from .metrics import RESOURCE_NAME_TO_METRICS
from .resource_filters import create_resource_filter
from .utils import (
    get_mapped_instance_tag,
    get_tags_recursively,
    is_metric_excluded_by_filters,
    is_resource_collected_by_filters,
    should_collect_per_instance_values,
)


class EsxiCheck(AgentCheck):
    __NAMESPACE__ = 'esxi'

    def __init__(self, name, init_config, instances):
        super(EsxiCheck, self).__init__(name, init_config, instances)
        self.host = self.instance.get("host")
        self.username = self.instance.get("username")
        self.password = self.instance.get("password")
        self.use_guest_hostname = self.instance.get("use_guest_hostname", False)
        self.excluded_host_tags = self._validate_excluded_host_tags(self.instance.get("excluded_host_tags", []))
        self.collect_per_instance_filters = self._parse_metric_regex_filters(
            self.instance.get("collect_per_instance_filters", {})
        )
        self.resource_filters = self._parse_resource_filters(self.instance.get("resource_filters", []))
        self.metric_filters = self._parse_metric_regex_filters(self.instance.get("metric_filters", {}))
        self.ssl_verify = is_affirmative(self.instance.get('ssl_verify', True))
        self.ssl_capath = self.instance.get("ssl_capath")
        self.ssl_cafile = self.instance.get("ssl_cafile")
        self.tags = [f"esxi_url:{self.host}"]

    def _validate_excluded_host_tags(self, excluded_host_tags):
        valid_excluded_host_tags = []
        for excluded_host_tag in excluded_host_tags:
            if excluded_host_tag not in AVAILABLE_HOST_TAGS:
                self.log.warning(
                    "Unknown host tag `%s` cannot be excluded. Available host tags are: "
                    "`esxi_url`, `esxi_type`, `esxi_host`, `esxi_folder`, `esxi_cluster` "
                    "`esxi_compute`, `esxi_datacenter`, and `esxi_datastore`",
                    excluded_host_tag,
                )
            else:
                valid_excluded_host_tags.append(excluded_host_tag)
        return valid_excluded_host_tags

    def _parse_metric_regex_filters(self, all_metric_filters):
        allowed_resource_types = RESOURCE_TYPE_TO_NAME.values()
        metric_filters = {}
        for resource_type, filters in iteritems(all_metric_filters):
            if resource_type not in allowed_resource_types:
                self.log.warning(
                    "Ignoring metric_filter for resource '%s'. It should be one of '%s'",
                    resource_type,
                    ", ".join(allowed_resource_types),
                )
                continue
            metric_filters[resource_type] = filters

        return {k: [re.compile(r) for r in v] for k, v in iteritems(metric_filters)}

    def _parse_resource_filters(self, all_resource_filters):
        # Keep a list of resource filters ids (tuple of resource, property and type) that are already registered.
        # This is to prevent users to define the same filter twice with different patterns.
        resource_filters_ids = []
        formatted_resource_filters = []
        allowed_resource_types = RESOURCE_TYPE_TO_NAME.values()

        for resource_filter in all_resource_filters:
            self.log.debug("processing filter %s", resource_filter)
            # Optional fields:
            if 'type' not in resource_filter:
                resource_filter['type'] = 'include'
            if 'property' not in resource_filter:
                resource_filter['property'] = 'name'

            missing_fields = False
            # Check required fields
            for field in ['resource', 'property', 'type', 'patterns']:
                if field not in resource_filter:
                    self.log.warning(
                        "Ignoring filter %r because it doesn't contain a %s field.", resource_filter, field
                    )
                    missing_fields = True
                    continue

            if missing_fields:
                continue

            # Check `resource` validity
            if resource_filter['resource'] not in allowed_resource_types:
                self.log.warning(
                    "Ignoring filter %r because resource %s is not a supported resource",
                    resource_filter,
                    resource_filter['resource'],
                )
                continue

            # Check `property` validity
            allowed_prop_names = []
            allowed_prop_names.extend(ALLOWED_FILTER_PROPERTIES)
            if resource_filter['resource'] == RESOURCE_TYPE_TO_NAME[vim.VirtualMachine]:
                allowed_prop_names.extend(EXTRA_FILTER_PROPERTIES_FOR_VMS)

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
                is_include=(resource_filter['type'] == 'include'),
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

    def get_resources(self):
        self.log.debug("Retrieving resources")
        property_specs = []

        for resource_type in ALL_RESOURCES:
            property_spec = vmodl.query.PropertyCollector.PropertySpec()
            property_spec.type = resource_type
            property_spec.pathSet = ["name", "parent"]
            property_specs.append(property_spec)
            if resource_type == VM_RESOURCE:
                property_spec.pathSet.append("runtime.host")
                property_spec.pathSet.append("guest.hostName")

        # Specify the attribute of the root object to traverse to obtain all the attributes
        traversal_spec = vmodl.query.PropertyCollector.TraversalSpec()
        traversal_spec.path = "view"
        traversal_spec.skip = False
        traversal_spec.type = vim.view.ContainerView

        retr_opts = vmodl.query.PropertyCollector.RetrieveOptions()
        retr_opts.maxObjects = MAX_PROPERTIES

        # Specify the root object from where we collect the rest of the objects
        obj_spec = vmodl.query.PropertyCollector.ObjectSpec()
        obj_spec.skip = True
        obj_spec.selectSet = [traversal_spec]

        # Create our filter spec from the above specs
        filter_spec = vmodl.query.PropertyCollector.FilterSpec()
        filter_spec.propSet = property_specs

        view_ref = self.content.viewManager.CreateContainerView(self.content.rootFolder, ALL_RESOURCES, True)

        try:
            obj_spec.obj = view_ref
            filter_spec.objectSet = [obj_spec]

            # Collect the object and its properties
            res = self.content.propertyCollector.RetrievePropertiesEx([filter_spec], retr_opts)
            if res is None:
                obj_content_list = []
            else:
                obj_content_list = res.objects
        finally:
            view_ref.Destroy()

        return obj_content_list

    def get_available_metric_ids_for_entity(self, entity):
        resource_name = RESOURCE_TYPE_TO_NAME[type(entity)]
        avaliable_metrics = RESOURCE_NAME_TO_METRICS[resource_name]

        counter_keys_and_names = {}
        for counter in self.content.perfManager.perfCounter:
            full_name = f"{counter.groupInfo.key}.{counter.nameInfo.key}.{SHORT_ROLLUP[counter.rollupType]}"
            if full_name in avaliable_metrics and not is_metric_excluded_by_filters(
                full_name, type(entity), self.metric_filters
            ):
                counter_keys_and_names[counter.key] = full_name
            else:
                self.log.trace("Skipping metric %s as it is not recognized or filtered", full_name)

        available_counter_ids = [m.counterId for m in self.content.perfManager.QueryAvailablePerfMetric(entity=entity)]
        counter_ids = [
            counter_id for counter_id in available_counter_ids if counter_id in counter_keys_and_names.keys()
        ]
        metric_ids = [vim.PerformanceManager.MetricId(counterId=counter, instance="") for counter in counter_ids]
        return counter_keys_and_names, metric_ids

    def collect_metrics_for_entity(self, metric_ids, counter_keys_and_names, entity, entity_name, metric_tags):
        resource_type = type(entity)
        resource_name = RESOURCE_TYPE_TO_NAME[resource_type]
        for metric_id in metric_ids:
            metric_name = counter_keys_and_names.get(metric_id.counterId)
            if should_collect_per_instance_values(self.collect_per_instance_filters, metric_name, resource_type):
                metric_id.instance = "*"

        spec = vim.PerformanceManager.QuerySpec(maxSample=1, entity=entity, metricId=metric_ids)
        result_stats = self.content.perfManager.QueryPerf([spec])

        # `have_instance_value` is used later to avoid collecting aggregated metrics
        # when instance metrics are collected.
        have_instance_value = defaultdict(set)
        if self.collect_per_instance_filters:
            for results_for_entity in result_stats:
                metric_resource_type = type(results_for_entity.entity)
                for metric_result in results_for_entity.value:
                    if metric_result.id.instance:
                        counter_id = counter_keys_and_names.get(metric_result.id.counterId)
                        if counter_id:
                            have_instance_value[metric_resource_type].add(counter_id)

        for results_for_entity in result_stats:
            for metric_result in results_for_entity.value:
                metric_name = counter_keys_and_names.get(metric_result.id.counterId)
                if self.log.isEnabledFor(logging.DEBUG):
                    # Use isEnabledFor to avoid unnecessary processing
                    self.log.debug(
                        "Processing metric `%s`: resource_type=`%s`, result=`%s`",
                        metric_name,
                        resource_type,
                        str(metric_result).replace("\n", "\\n"),
                    )

                if not metric_name:
                    # Fail-safe
                    self.log.debug(
                        "Skipping value for counter %s, because the integration doesn't have metadata about it",
                        metric_result.id.counterId,
                    )
                    continue

                additional_tags = []
                if should_collect_per_instance_values(
                    self.collect_per_instance_filters, metric_name, resource_type
                ) and (metric_name in have_instance_value[resource_type]):
                    instance_value = metric_result.id.instance
                    # When collecting per instance values, it's possible that both aggregated metric and per instance
                    # metrics are received. In that case, the metric with no instance value is skipped.
                    if not instance_value:
                        continue
                    instance_tag_key = get_mapped_instance_tag(metric_name)
                    additional_tags.append(f'{instance_tag_key}:{instance_value}')

                if len(metric_result.value) == 0:
                    self.log.debug(
                        "Skipping metric %s for %s because no value was returned by the %s",
                        metric_name,
                        entity_name,
                        resource_name,
                    )
                    continue

                valid_values = [v for v in metric_result.value if v >= 0]
                if len(valid_values) <= 0:
                    self.log.debug(
                        "Skipping metric %s for %s, because the value returned by the %s"
                        " is negative (i.e. the metric is not yet available). values: %s",
                        metric_name,
                        entity_name,
                        resource_name,
                        list(metric_result.value),
                    )
                    continue
                else:
                    most_recent_val = valid_values[-1]
                    all_tags = metric_tags + additional_tags

                    self.log.debug(
                        "Submit metric: name=`%s`, value=`%s`, hostname=`%s`, tags=`%s`",
                        metric_name,
                        most_recent_val,
                        entity_name,
                        all_tags,
                    )
                    self.gauge(metric_name, most_recent_val, hostname=entity_name, tags=all_tags)

    def set_version_metadata(self):
        esxi_version = self.content.about.version
        build_version = self.content.about.build
        self.set_metadata('version', f'{esxi_version}+{build_version}')

    def check(self, _):
        try:
            context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = True if self.ssl_verify else False
            context.verify_mode = ssl.CERT_REQUIRED if self.ssl_verify else ssl.CERT_NONE

            if self.ssl_capath:
                context.load_verify_locations(cafile=None, capath=self.ssl_capath, cadata=None)
            elif self.ssl_cafile:
                context.load_verify_locations(cafile=self.ssl_cafile, capath=None, cadata=None)
            else:
                context.load_default_certs(ssl.Purpose.SERVER_AUTH)

            connection = connect.SmartConnect(host=self.host, user=self.username, pwd=self.password, sslContext=context)
            self.conn = connection
            self.content = connection.content

            if self.content.about.apiType != "HostAgent":
                raise Exception(
                    f"{self.host} is not an ESXi host; please set the `host` config option to an ESXi host "
                    "or use the vSphere integration to collect data from the vCenter",
                )

            self.log.info("Connected to ESXi host %s: %s", self.host, self.content.about.fullName)
            self.count("host.can_connect", 1, tags=self.tags)

        except Exception as e:
            self.log.exception("Cannot connect to ESXi host %s: %s", self.host, str(e))
            self.count("host.can_connect", 0, tags=self.tags)
            raise

        self.set_version_metadata()
        resources = self.get_resources()
        resource_map = {
            obj_content.obj: {prop.name: prop.val for prop in obj_content.propSet}
            for obj_content in resources
            if obj_content.propSet
        }

        if not resource_map:
            self.log.warning("No resources found; halting check execution")
            return

        # Add the root folder entity as it can't be fetched from the previous api calls.
        root_folder = self.content.rootFolder
        resource_map[root_folder] = {"name": root_folder.name, "parent": None}
        self.log.debug("All resources: %s", resource_map)

        external_host_tags = []

        all_resources_with_metrics = {
            resource_obj: resource_props
            for (resource_obj, resource_props) in resource_map.items()
            if type(resource_obj) in [VM_RESOURCE, HOST_RESOURCE]
        }

        for resource_obj, resource_props in all_resources_with_metrics.items():

            if not is_resource_collected_by_filters(resource_obj, all_resources_with_metrics, self.resource_filters):
                self.log.debug(
                    "Skipping metric collection for resource %s as it is not matched by filters", resource_obj
                )
                continue

            hostname = resource_props.get("name")

            resource_type = RESOURCE_TYPE_TO_NAME[type(resource_obj)]
            if resource_type == "vm" and self.use_guest_hostname:
                hostname = resource_props.get("guest.hostName", hostname)

            self.log.debug("Collect metrics and host tags for hostname: %s, object: %s", hostname, resource_obj)

            tags = []
            parent = resource_props.get('parent')

            if resource_type == "vm":
                runtime_host = resource_props.get('runtime.host')
                runtime_host_props = {}
                if runtime_host:
                    if runtime_host in all_resources_with_metrics:
                        runtime_host_props = all_resources_with_metrics.get(runtime_host, {})
                    else:
                        self.log.debug("Missing runtime.host details for VM %s", hostname)

                runtime_hostname = to_string(runtime_host_props.get("name", "unknown"))
                tags.append('esxi_host:{}'.format(runtime_hostname))

                if runtime_host is not None:
                    tags.extend(
                        get_tags_recursively(
                            runtime_host,
                            resource_map,
                            include_only=['esxi_cluster'],
                        )
                    )

            if parent is not None:
                tags.extend(get_tags_recursively(parent, resource_map))

            tags.append('esxi_type:{}'.format(resource_type))

            metric_tags = self.tags
            if self.excluded_host_tags:
                metric_tags = metric_tags + [t for t in tags if t.split(":", 1)[0] in self.excluded_host_tags]

            tags.extend(self.tags)

            if hostname is not None:
                filtered_external_tags = [t for t in tags if t.split(':')[0] not in self.excluded_host_tags]
                external_host_tags.append((hostname, {self.__NAMESPACE__: filtered_external_tags}))
            else:
                self.log.debug("No host name found for %s; skipping external tag submission", resource_obj)

            self.count(f"{resource_type}.count", 1, tags=tags, hostname=None)

            counter_keys_and_names, metric_ids = self.get_available_metric_ids_for_entity(resource_obj)
            self.collect_metrics_for_entity(metric_ids, counter_keys_and_names, resource_obj, hostname, metric_tags)

        if external_host_tags:
            self.set_external_tags(external_host_tags)
