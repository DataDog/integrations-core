# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from six import PY3, iteritems

from datadog_checks.base.utils.serialization import json

if PY3:
    import time

    from datadog_checks.cisco_aci.models import DeviceMetadata, InterfaceMetadata, NetworkDevicesMetadata, Node, PhysIf

else:
    DeviceMetadata = None
    Eth = None
    InterfaceMetadata = None
    Node = None

from . import aci_metrics, exceptions, helpers

VENDOR_CISCO = 'cisco'
PAYLOAD_METADATA_BATCH_SIZE = 100


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
        return PY3 and self.send_ndm_metadata

    def collect(self):
        fabric_pods = self.api.get_fabric_pods()
        fabric_nodes = self.api.get_fabric_nodes()
        self.log.info("%s pods and %s nodes computed", len(fabric_nodes), len(fabric_pods))
        pods = self.submit_pod_health(fabric_pods)
        devices, interfaces = self.submit_nodes_health_and_metadata(fabric_nodes, pods)
        if self.ndm_enabled():
            collect_timestamp = int(time.time())
            batches = self.batch_payloads(devices, interfaces, collect_timestamp)
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

            user_tags = self.instance.get('tags', [])
            tags = self.tagger.get_fabric_tags(n, 'fabricNode')
            tags.extend(self.ndm_common_tags(node_attrs.get('address', ''), hostname, self.namespace))
            self.external_host_tags[hostname] = tags + self.check_tags + user_tags

            pod_id = helpers.get_pod_from_dn(node_attrs['dn'])
            if not node_id or not pod_id:
                continue
            self.log.info("processing node %s on pod %s", node_id, pod_id)
            try:
                if self.ndm_enabled():
                    device_metadata.append(self.submit_node_metadata(node_attrs, tags))
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
        pod_id = helpers.get_pod_from_dn(node['dn'])
        common_tags = self.ndm_common_tags(node.get('address', ''), hostname, self.namespace)
        try:
            eth_list = self.api.get_eth_list(pod_id, node['id'])
        except (exceptions.APIConnectionException, exceptions.APIParsingException):
            pass
        interfaces = []
        for e in eth_list:
            eth_attrs = helpers.get_attributes(e)
            eth_id = eth_attrs['id']
            tags = self.tagger.get_fabric_tags(e, 'l1PhysIf')
            tags.extend(common_tags)
            if self.ndm_enabled():
                interfaces.append(self.create_interface_metadata(e, node.get('address', ''), tags, hostname))
            try:
                stats = self.api.get_eth_stats(pod_id, node['id'], eth_id)
                self.submit_fabric_metric(stats, tags, 'l1PhysIf', hostname=hostname)
            except (exceptions.APIConnectionException, exceptions.APIParsingException):
                pass
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

    def batch_payloads(self, devices, interfaces, collect_ts):
        for device in devices:
            yield NetworkDevicesMetadata(namespace=self.namespace, devices=[device], collect_timestamp=collect_ts)

        payloads = []
        for interface in interfaces:
            if len(payloads) == PAYLOAD_METADATA_BATCH_SIZE:
                yield NetworkDevicesMetadata(
                    namespace=self.namespace, interfaces=payloads, collect_timestamp=collect_ts
                )
                payloads = []
            payloads.append(interface)
        if payloads:
            yield NetworkDevicesMetadata(namespace=self.namespace, interfaces=payloads, collect_timestamp=collect_ts)

    def submit_node_metadata(self, node_attrs, tags):
        node = Node(attributes=node_attrs)
        hostname = helpers.get_hostname_from_dn(node.attributes.dn)
        id_tags = self.ndm_common_tags(node.attributes.address, hostname, self.namespace)
        device_tags = [
            'device_vendor:{}'.format(VENDOR_CISCO),
            "source:cisco-aci",
        ]
        device = DeviceMetadata(
            id='{}:{}'.format(self.namespace, node.attributes.address),
            id_tags=id_tags,
            tags=device_tags + tags,
            name=hostname,
            ip_address=node.attributes.address,
            model=node.attributes.model,
            fabric_st=node.attributes.fabric_st,
            vendor=VENDOR_CISCO,
            version=node.attributes.version,
            serial_number=node.attributes.serial,
            device_type=node.attributes.device_type,
        )
        return device.model_dump(exclude_none=True)

    def create_interface_metadata(self, phys_if, address, tags, hostname):
        eth = PhysIf(**phys_if.get('l1PhysIf', {}))
        interface = InterfaceMetadata(
            device_id='{}:{}'.format(self.namespace, address),
            id_tags=['interface:{}'.format(eth.attributes.name)],
            index=eth.attributes.id,
            name=eth.attributes.name,
            description=eth.attributes.desc,
            mac_address=eth.attributes.router_mac,
            admin_status=eth.attributes.admin_st,
        )
        if eth.ethpm_phys_if:
            interface.oper_status = eth.ethpm_phys_if.attributes.oper_st
        if interface.status:
            new_tags = tags.copy()
            new_tags.extend(["port.status:{}".format(interface.status)])
            self.gauge('cisco_aci.fabric.port.status', 1, tags=new_tags, hostname=hostname)
        return interface.model_dump(exclude_none=True)

    def ndm_common_tags(self, address, hostname, namespace):
        return [
            'device_ip:{}'.format(address),
            'device_namespace:{}'.format(namespace),
            'device_hostname:{}'.format(hostname),
            'device_id:{}:{}'.format(namespace, address),
        ]
