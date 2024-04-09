# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pyVim import connect
from pyVmomi import vim, vmodl

from datadog_checks.base import AgentCheck  # noqa: F401

from .constants import ALL_RESOURCES, HOST_RESOURCE, MAX_PROPERTIES, RESOURCE_TYPE_TO_NAME, SHORT_ROLLUP, VM_RESOURCE
from .metrics import RESOURCE_NAME_TO_METRICS
from .utils import get_tags_recursively


class EsxiCheck(AgentCheck):
    __NAMESPACE__ = 'esxi'

    def __init__(self, name, init_config, instances):
        super(EsxiCheck, self).__init__(name, init_config, instances)
        self.host = self.instance.get("host")
        self.username = self.instance.get("username")
        self.password = self.instance.get("password")
        self.use_guest_hostname = self.instance.get("use_guest_hostname", False)
        self.excluded_host_tags = self.instance.get("excluded_host_tags", [])
        self.tags = [f"esxi_url:{self.host}"]

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
            if full_name in avaliable_metrics:
                counter_keys_and_names[counter.key] = full_name
            else:
                self.log.trace("Skipping metric %s as it is not recognized", full_name)

        available_counter_ids = [m.counterId for m in self.content.perfManager.QueryAvailablePerfMetric(entity=entity)]
        counter_ids = [
            counter_id for counter_id in available_counter_ids if counter_id in counter_keys_and_names.keys()
        ]
        metric_ids = [vim.PerformanceManager.MetricId(counterId=counter, instance="") for counter in counter_ids]
        return counter_keys_and_names, metric_ids

    def collect_metrics_for_entity(self, metric_ids, counter_keys_and_names, entity, entity_name, metric_tags):

        resource_name = RESOURCE_TYPE_TO_NAME[type(entity)]
        spec = vim.PerformanceManager.QuerySpec(maxSample=1, entity=entity, metricId=metric_ids)
        result_stats = self.content.perfManager.QueryPerf([spec])

        for results_for_entity in result_stats:
            for metric_result in results_for_entity.value:
                metric_name = counter_keys_and_names.get(metric_result.id.counterId)
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

                    self.log.debug(
                        "Submit metric: name=`%s`, value=`%s`, hostname=`%s`, tags=`%s`",
                        metric_name,
                        most_recent_val,
                        entity_name,
                        self.tags,
                    )
                    self.gauge(metric_name, most_recent_val, hostname=entity_name, tags=metric_tags)

    def check(self, _):
        try:
            connection = connect.SmartConnect(host=self.host, user=self.username, pwd=self.password)
            self.conn = connection
            self.log.info("Connected to ESXi host %s", self.host)
            self.count("host.can_connect", 1, tags=self.tags)

        except Exception as e:
            self.log.warning("Cannot connect to ESXi host %s: %s", self.host, str(e))
            self.count("host.can_connect", 0, tags=self.tags)
            return

        self.content = connection.content

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
            hostname = resource_props.get("name")

            resource_type = RESOURCE_TYPE_TO_NAME[type(resource_obj)]
            if resource_type == "vm" and self.use_guest_hostname:
                hostname = resource_props.get("guest.hostName", hostname)

            self.log.debug("Collect metrics and host tags for hostname: %s, object: %s", hostname, resource_obj)

            tags = []
            parent = resource_props.get('parent')
            runtime_host = resource_props.get('runtime.host')
            if parent is not None:
                tags.extend(get_tags_recursively(parent, resource_map))
            if runtime_host is not None:
                tags.extend(
                    get_tags_recursively(
                        runtime_host,
                        resource_map,
                        include_only=['esxi_cluster'],
                    )
                )
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
