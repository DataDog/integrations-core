# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.cisco_aci.models import (
    DeviceMetadata,
    InterfaceMetadata,
    LldpAdjEp,
    NetworkDevicesMetadata,
    Node,
    PhysIf,
    SourceType,
    TopologyLinkDevice,
    TopologyLinkInterface,
    TopologyLinkMetadata,
    TopologyLinkSide,
)

from . import helpers

VENDOR_CISCO = 'cisco'
PAYLOAD_METADATA_BATCH_SIZE = 100


def create_node_metadata(node_attrs, tags, namespace):
    """
    Create a DeviceMetadata object from a node's attributes
    """
    node = Node(attributes=node_attrs)
    hostname = node.attributes.name
    id_tags = common_tags(node.attributes.address, hostname, namespace)
    device_tags = [
        'device_vendor:{}'.format(VENDOR_CISCO),
        "source:cisco-aci",
    ]
    device = DeviceMetadata(
        id='{}:{}'.format(namespace, node.attributes.address),
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
        pod_node_id=helpers.get_hostname_from_dn(node.attributes.dn),
    )
    return device


def create_interface_metadata(phys_if, address, namespace):
    """
    Create an InterfaceMetadata object from a physical interface
    """
    eth = PhysIf(**phys_if.get('l1PhysIf', {}))
    interface = InterfaceMetadata(
        device_id='{}:{}'.format(namespace, address),
        id_tags=['interface:{}'.format(eth.attributes.name)],
        index=eth.attributes.id,
        name=eth.attributes.name,
        description=eth.attributes.desc,
        mac_address=eth.attributes.router_mac,
        admin_status=eth.attributes.admin_st,
    )
    if eth.ethpm_phys_if:
        interface.oper_status = eth.ethpm_phys_if.attributes.oper_st

    return interface


def create_topology_link_metadata(lldp_adj_eps, cdp_adj_eps, device_map, namespace):
    """
    Create a TopologyLinkMetadata object from LLDP or CDP
    """
    lldp_adj_eps_list = LldpAdjEp()
    for lldp_adj_ep in lldp_adj_eps_list:
        local_device_id = device_map.get(lldp_adj_ep.attributes.local_device_dn)
        remote_entry_unique_id = lldp_adj_ep.attributes.local_port_id + "." + lldp_adj_ep.attributes.remote_port_id

        local = TopologyLinkSide(
            # TODO: need to grab the device id from mapping
            device=TopologyLinkDevice(dd_id=local_device_id),
            # TODO: double check resolve the local interface id
            interface=TopologyLinkInterface(
                dd_id='', id=lldp_adj_ep.attributes.local_port_id, id_type='interface_name'
            ),
        )
        remote = TopologyLinkSide(
            # this is all good afaik
            device=TopologyLinkDevice(
                name=lldp_adj_ep.attributes.system_name,
                description=lldp_adj_ep.attributes.system_desc,
                id=lldp_adj_ep.attributes.chassis_id_v,
                id_type=lldp_adj_ep.attributes.chassis_id_t,
                ip_address=lldp_adj_ep.attributes.mgmt_ip,
            ),
            # TODO: check on the interface alias/name for resolution vs. taken what's given to us
            interface=TopologyLinkInterface(
                id=lldp_adj_ep.attributes.remote_port_id,
                id_type=lldp_adj_ep.attributes.port_id_t,
                description=lldp_adj_ep.attributes.port_desc,
            ),
        )
        yield TopologyLinkMetadata(
            id='{}:{}'.format(local_device_id, remote_entry_unique_id),
            source_type=SourceType.LLDP,
            local=local,
            remote=remote,
        )


def get_device_ip_mapping(devices):
    devices_map = {}
    for device in devices:
        key = device.pod_node_id
        devices_map[key] = device.ip_address
    return devices_map


def get_device_info(device):
    """
    Get device ID and node ID from a device object
    """
    for tag in device.tags:
        if tag.startswith('node_id'):
            node_id = tag.split(':')[1]
            break
    return device.id, node_id


def batch_payloads(namespace, devices, interfaces, links, collect_ts):
    """
    Batch payloads into NetworkDevicesMetadata objects
    """
    network_devices_metadata = NetworkDevicesMetadata(namespace=namespace, collect_timestamp=collect_ts)
    for device in devices:
        current_payload, new_payload = append_to_payload(device, network_devices_metadata, namespace, collect_ts)
        if new_payload:
            yield current_payload
            network_devices_metadata = new_payload

    for interface in interfaces:
        current_payload, new_payload = append_to_payload(interface, network_devices_metadata, namespace, collect_ts)
        if new_payload:
            yield current_payload
            network_devices_metadata = new_payload

    for link in links:
        current_payload, new_payload = append_to_payload(link, network_devices_metadata, namespace, collect_ts)
        if new_payload:
            yield current_payload
            network_devices_metadata = new_payload

    yield network_devices_metadata


def append_to_payload(item, current_payload, namespace, collect_ts):
    """
    Append metadata to a NetworkDevicesMetadata payload, creating a new payload if batch size is reached
    """
    if current_payload.size < PAYLOAD_METADATA_BATCH_SIZE:
        current_payload.append_metadata(item)
        return current_payload, None
    else:
        new_payload = NetworkDevicesMetadata(namespace=namespace, collect_timestamp=collect_ts)
        new_payload.append_metadata(item)
        return current_payload, new_payload


def common_tags(address, hostname, namespace):
    """
    Return a list of common tags (following NDM standards) for a device
    """
    return [
        'device_ip:{}'.format(address),
        'device_namespace:{}'.format(namespace),
        'device_hostname:{}'.format(hostname),
        'device_id:{}:{}'.format(namespace, address),
    ]
