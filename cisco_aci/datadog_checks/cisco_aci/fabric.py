# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from six import iteritems

from datadog_checks.base.utils.serialization import json
from datadog_checks.cisco_aci.models import DeviceMetadata, Eth, InterfaceMetadata, Node

from . import aci_metrics, exceptions, helpers


class Fabric:
    """
    Collect fabric metrics from the APIC
    """

    def __init__(self, check, api, instance):
        self.check = check
        self.api = api
        self.instance = instance
        self.check_tags = check.check_tags

        # grab some functions from the check
        self.gauge = check.gauge
        self.rate = check.rate
        self.log = check.log
        self.submit_metrics = check.submit_metrics
        self.tagger = self.check.tagger
        self.external_host_tags = self.check.external_host_tags
        self.ndm_metadata = check.ndm_metadata

    def collect(self):
        fabric_pods = self.api.get_fabric_pods()
        fabric_nodes = self.api.get_fabric_nodes()
        self.log.info("%s pods and %s nodes computed", len(fabric_nodes), len(fabric_pods))
        pods = self.submit_pod_health(fabric_pods)
        self.submit_nodes_health(fabric_nodes, pods)

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

    def submit_nodes_health(self, nodes, pods):
        for n in nodes:
            hostname = helpers.get_fabric_hostname(n)

            user_tags = self.instance.get('tags', [])
            tags = self.tagger.get_fabric_tags(n, 'fabricNode')
            self.external_host_tags[hostname] = tags + self.check_tags + user_tags

            node = n.get('fabricNode', {})
            node_attrs = node.get('attributes', {})
            node_id = node_attrs.get('id', {})

            pod_id = helpers.get_pod_from_dn(node_attrs['dn'])
            if not node_id or not pod_id:
                continue
            self.log.info("processing node %s on pod %s", node_id, pod_id)
            try:
                self.submit_node_metadata(node_attrs, tags)
                self.submit_process_metric(n, tags + self.check_tags + user_tags, hostname=hostname)
            except (exceptions.APIConnectionException, exceptions.APIParsingException):
                pass
            if node_attrs.get('role') != "controller":
                try:
                    stats = self.api.get_node_stats(pod_id, node_id)
                    self.submit_fabric_metric(stats, tags, 'fabricNode', hostname=hostname)
                    self.process_eth(node_attrs)
                except (exceptions.APIConnectionException, exceptions.APIParsingException):
                    pass
            self.log.info("finished processing node %s", node_id)

    def process_eth(self, node):
        self.log.info("processing ethernet ports for %s", node.get('id'))
        hostname = helpers.get_fabric_hostname(node)
        pod_id = helpers.get_pod_from_dn(node['dn'])
        try:
            eth_list = self.api.get_eth_list(pod_id, node['id'])
        except (exceptions.APIConnectionException, exceptions.APIParsingException):
            pass
        for e in eth_list:
            eth_attrs = helpers.get_attributes(e)
            eth_id = eth_attrs['id']
            tags = self.tagger.get_fabric_tags(e, 'l1PhysIf')
            self.submit_interface_metadata(eth_attrs, node['address'], tags)
            try:
                stats = self.api.get_eth_stats(pod_id, node['id'], eth_id)
                self.submit_fabric_metric(stats, tags, 'l1PhysIf', hostname=hostname)
            except (exceptions.APIConnectionException, exceptions.APIParsingException):
                pass
        self.log.info("finished processing ethernet ports for %s", node['id'])

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
            for n, ms in iteritems(aci_metrics.FABRIC_METRICS):
                if n not in name:
                    continue
                for cisco_metric, dd_metric in iteritems(ms):
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

    def submit_node_metadata(self, node_attrs, tags):
        vendor = 'cisco_aci'
        namespace = 'default'
        node = Node(attributes=node_attrs)
        id_tags = ['namespace:{}'.format(namespace), 'system_ip:{}'.format(node.attributes.address)]
        device_tags = [
            'device_vendor:{}'.format(vendor),
            'device_namespace:{}'.format(namespace),
            'device_hostname:{}'.format(node.attributes.dn),
            'hostname:{}'.format(node.attributes.dn),
            'system_ip:{}'.format(node.attributes.address),
            'device_ip:{}'.format(node.attributes.address),
            'device_id:{}:{}'.format(namespace, node.attributes.address),
        ]
        device = DeviceMetadata(
            device_id='{}:{}'.format(namespace, node.attributes.address),
            id_tags=id_tags,
            tags=device_tags + tags,
            name=node.attributes.dn,
            ip_address=node.attributes.address,
            model=node.attributes.model,
            ad_st=node.attributes.ad_st,
            vendor=vendor,
            version=node.attributes.version,
            serial_number=node.attributes.serial,
        )
        self.ndm_metadata(json.dumps(device.model_dump()))

    def submit_interface_metadata(self, eth_attr, address, tags):
        eth = Eth(attributes=eth_attr)
        namespace = 'default'
        interface = InterfaceMetadata(
            device_id='{}:{}'.format(namespace, address),
            id_tags=tags,
            index=eth.attributes.id,
            name=eth.attributes.name,
            description=eth.attributes.desc,
            mac_address=eth.attributes.router_mac,
            admin_status=eth.attributes.admin_st,
        )
        self.ndm_metadata(json.dumps(interface.model_dump()))
