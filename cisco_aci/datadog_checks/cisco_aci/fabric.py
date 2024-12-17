# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

from datadog_checks.base.utils.serialization import json

from . import aci_metrics, exceptions, helpers, ndm

VENDOR_CISCO = 'cisco'
PAYLOAD_METADATA_BATCH_SIZE = 100
DEVICE_USER_TAGS_PREFIX = "dd.internal.resource:ndm_device_user_tags"
INTERFACE_USER_TAGS_PREFIX = "dd.internal.resource:ndm_interface_user_tags"


class Fabric:
    """
    Collect fabric metrics from the APIC
    """

    def __init__(self, check, api, instance, namespace):
        self.check = check
        self.api = api
        self.instance = instance
        self.check_tags = check.check_tags
        self.namespace = namespace

        # Config for submitting device/interface metadata to NDM
        self.send_ndm_metadata = self.instance.get('send_ndm_metadata', False)

        # grab some functions from the check
        self.gauge = check.gauge
        self.rate = check.rate
        self.log = check.log
        self.submit_metrics = check.submit_metrics
        self.tagger = self.check.tagger
        self.external_host_tags = self.check.external_host_tags
        self.event_platform_event = check.event_platform_event

    def ndm_enabled(self):
        return self.send_ndm_metadata

    def collect(self):
        fabric_pods = self.api.get_fabric_pods()
        fabric_nodes = self.api.get_fabric_nodes()
        self.log.info("%s pods and %s nodes computed", len(fabric_nodes), len(fabric_pods))
        pods = self.submit_pod_health(fabric_pods)
        devices, interfaces = self.submit_nodes_health_and_metadata(fabric_nodes, pods)
        if self.ndm_enabled():
            # get topology link metadata
            lldp_adj_eps = self.api.get_lldp_adj_eps()
            cdp_adj_eps = self.api.get_cdp_adj_eps()
            device_map = ndm.get_device_ip_mapping(devices)
            links = ndm.create_topology_link_metadata(lldp_adj_eps, cdp_adj_eps, device_map, self.namespace)

            collect_timestamp = int(time.time())
            batches = ndm.batch_payloads(self.namespace, devices, interfaces, links, collect_timestamp)
            for batch in batches:
                self.event_platform_event(json.dumps(batch.model_dump(exclude_none=True)), "network-devices-metadata")

    def submit_pod_health(self, pods):
        pods_dict = {}
        for p in pods:
            pod = p.get('fabricPod', {})
            pod_attrs = pod.get('attributes', {})
            pod_id = pod_attrs.get('id')
            if not pod_id:
                continue
            pods_dict[pod_id] = pod_attrs
            self.log.info("processing pod %s", pod_id)
            tags = self.tagger.get_fabric_tags(p, 'fabricPod')
            try:
                stats = self.api.get_pod_stats(pod_id)
                self.submit_fabric_metric(stats, tags, 'fabricPod')
            except (exceptions.APIConnectionException, exceptions.APIParsingException):
                pass
            self.log.info("finished processing pod %s", pod_id)

        return pods_dict

    def submit_nodes_health_and_metadata(self, nodes, pods):
        device_metadata = []
        interface_metadata = []
        for n in nodes:
            hostname = helpers.get_fabric_hostname(n)

            node = n.get('fabricNode', {})
            node_attrs = node.get('attributes', {})
            node_id = node_attrs.get('id', {})

            device_hostname = node_attrs.get('name', '')

            user_tags = self.instance.get('tags', [])
            tags = self.tagger.get_fabric_tags(n, 'fabricNode')
            tags.extend(ndm.common_tags(node_attrs.get('address', ''), device_hostname, self.namespace))
            self.external_host_tags[hostname] = tags + self.check_tags + user_tags

            pod_id = helpers.get_pod_from_dn(node_attrs['dn'])
            if not node_id or not pod_id:
                continue
            self.log.info("processing node %s on pod %s", node_id, pod_id)
            try:
                if self.ndm_enabled():
                    device_metadata.append(ndm.create_node_metadata(node_attrs, tags, self.namespace))

                    device_id = '{}:{}'.format(self.namespace, node_attrs.get('address', ''))
                    tags.append('{}:{}'.format(DEVICE_USER_TAGS_PREFIX, device_id))

                self.submit_process_metric(n, tags + self.check_tags + user_tags, hostname=hostname)
            except (exceptions.APIConnectionException, exceptions.APIParsingException):
                pass
            if node_attrs.get('role') != "controller":
                try:
                    stats = self.api.get_node_stats(pod_id, node_id)
                    self.submit_fabric_metric(stats, tags, 'fabricNode', hostname=hostname)
                    eth_metadata = self.process_eth(node_attrs)
                    if self.ndm_enabled():
                        interface_metadata.extend(eth_metadata)
                except (exceptions.APIConnectionException, exceptions.APIParsingException):
                    pass
            self.log.info("finished processing node %s", node_id)
        return device_metadata, interface_metadata

    def process_eth(self, node):
        self.log.info("processing ethernet ports for %s", node.get('id'))
        hostname = helpers.get_fabric_hostname(node)
        device_hostname = node.get('name', '')
        pod_id = helpers.get_pod_from_dn(node['dn'])
        common_tags = ndm.common_tags(node.get('address', ''), device_hostname, self.namespace)
        try:
            eth_list_and_stats = self.api.get_eth_list_and_stats(pod_id, node['id'])
        except (exceptions.APIConnectionException, exceptions.APIParsingException):
            pass
        interfaces = []
        for e in eth_list_and_stats:
            tags = self.tagger.get_fabric_tags(e, 'l1PhysIf')
            tags.extend(common_tags)

            if self.ndm_enabled():
                interface_metadata = ndm.create_interface_metadata(e, node.get('address', ''), self.namespace)
                interfaces.append(interface_metadata)
                device_id = '{}:{}'.format(self.namespace, node.get('address', ''))
                tags.append('{}:{}'.format(DEVICE_USER_TAGS_PREFIX, device_id))
                tags.append(
                    "{}:{}:{}".format(
                        INTERFACE_USER_TAGS_PREFIX, interface_metadata.device_id, str(interface_metadata.index)
                    ),
                )
                self.submit_interface_status_metric(
                    interface_metadata.status,
                    tags,
                    device_hostname,
                )
            stats = e.get('l1PhysIf', {}).get('children', [])
            self.submit_fabric_metric(stats, tags, 'l1PhysIf', hostname=hostname)
        self.log.info("finished processing ethernet ports for %s", node['id'])
        return interfaces

    def submit_fabric_metric(self, stats, tags, obj_type, hostname=None):
        for s in stats:
            name = list(s.keys())[0]
            # we only want to collect the 5 minutes metrics.
            if '15min' in name or '5min' not in name:
                continue
            attrs = s[name]['attributes']
            if 'index' in attrs:
                continue

            metrics = {}
            for n, ms in aci_metrics.FABRIC_METRICS.items():
                if n not in name:
                    continue
                for cisco_metric, dd_metric in ms.items():
                    mname = dd_metric.format(self.get_fabric_type(obj_type))
                    mval = s.get(name, {}).get("attributes", {}).get(cisco_metric)
                    json_attrs = s.get(name, {}).get("attributes", {})
                    if mval and helpers.check_metric_can_be_zero(cisco_metric, mval, json_attrs):
                        metrics[mname] = mval

            self.submit_metrics(metrics, tags, hostname=hostname, instance=self.instance)

    def submit_process_metric(self, obj, tags, hostname=None):
        attrs = helpers.get_attributes(obj)
        node_id = helpers.get_node_from_dn(attrs['dn'])
        pod_id = helpers.get_pod_from_dn(attrs['dn'])

        if attrs['role'] == "controller":
            metrics = self.api.get_controller_proc_metrics(pod_id, node_id)
        else:
            metrics = self.api.get_spine_proc_metrics(pod_id, node_id)

        for d in metrics:
            if d.get("procCPUHist5min", {}).get('attributes'):
                data = d.get("procCPUHist5min").get("attributes", {})
                if data.get('index') == '0':
                    value = data.get('currentAvg')
                    if value:
                        self.gauge('cisco_aci.fabric.node.cpu.avg', value, tags=tags, hostname=hostname)
                    value = data.get('currentMax')
                    if value:
                        self.gauge('cisco_aci.fabric.node.cpu.max', value, tags=tags, hostname=hostname)
                    value = data.get('currentMin')
                    if value:
                        self.gauge('cisco_aci.fabric.node.cpu.min', value, tags=tags, hostname=hostname)

            if d.get("procSysCPUHist5min", {}).get('attributes'):
                data = d.get("procSysCPUHist5min").get("attributes", {})
                value = data.get('idleMax')
                if value:
                    self.gauge('cisco_aci.fabric.node.cpu.idle.max', value, tags=tags, hostname=hostname)
                    not_idle = 100.0 - float(value)
                    self.gauge('cisco_aci.fabric.node.cpu.max', not_idle, tags=tags, hostname=hostname)
                value = data.get('idleMin')
                if value:
                    self.gauge('cisco_aci.fabric.node.cpu.idle.min', value, tags=tags, hostname=hostname)
                    not_idle = 100.0 - float(value)
                    self.gauge('cisco_aci.fabric.node.cpu.min', not_idle, tags=tags, hostname=hostname)
                value = data.get('idleAvg')
                if value:
                    self.gauge('cisco_aci.fabric.node.cpu.idle.avg', value, tags=tags, hostname=hostname)
                    not_idle = 100.0 - float(value)
                    self.gauge('cisco_aci.fabric.node.cpu.avg', not_idle, tags=tags, hostname=hostname)

            if d.get("procMemHist5min", {}).get('attributes'):
                data = d.get("procMemHist5min").get("attributes", {})
                if data.get('index') == '0':
                    value = data.get('currentAvg')
                    if value:
                        self.gauge('cisco_aci.fabric.node.mem.avg', value, tags=tags, hostname=hostname)
                    value = data.get('currentMax')
                    if value:
                        self.gauge('cisco_aci.fabric.node.mem.max', value, tags=tags, hostname=hostname)
                    value = data.get('currentMin')
                    if value:
                        self.gauge('cisco_aci.fabric.node.mem.min', value, tags=tags, hostname=hostname)

            if d.get("procSysMemHist5min", {}).get('attributes'):
                data = d.get("procSysMemHist5min").get("attributes", {})
                if data.get('index') == '0':
                    value = data.get('usedAvg')
                    if value:
                        self.gauge('cisco_aci.fabric.node.mem.avg', value, tags=tags, hostname=hostname)
                    value = data.get('usedMax')
                    if value:
                        self.gauge('cisco_aci.fabric.node.mem.max', value, tags=tags, hostname=hostname)
                    value = data.get('usedMin')
                    if value:
                        self.gauge('cisco_aci.fabric.node.mem.min', value, tags=tags, hostname=hostname)

                    value = data.get('freeAvg')
                    if value:
                        self.gauge('cisco_aci.fabric.node.mem.free.avg', value, tags=tags, hostname=hostname)
                    value = data.get('freeMax')
                    if value:
                        self.gauge('cisco_aci.fabric.node.mem.free.max', value, tags=tags, hostname=hostname)
                    value = data.get('freeMin')
                    if value:
                        self.gauge('cisco_aci.fabric.node.mem.free.min', value, tags=tags, hostname=hostname)

    def get_fabric_type(self, obj_type):
        if obj_type == 'fabricNode':
            return 'node'
        if obj_type == 'fabricPod':
            return 'pod'
        if obj_type == 'l1PhysIf':
            return 'port'

    def submit_interface_status_metric(self, status, tags, hostname):
        if status:
            new_tags = tags.copy()
            new_tags.extend(["status:{}".format(status)])
            self.gauge('cisco_aci.fabric.port.status', 1, tags=new_tags, hostname=hostname)
