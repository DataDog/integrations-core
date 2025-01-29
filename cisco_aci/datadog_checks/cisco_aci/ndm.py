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
        status=node.attributes.status,
        model=node.attributes.model,
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
        raw_id=eth.attributes.id,
        id_tags=['interface:{}'.format(eth.attributes.name)],
        index=eth.attributes.id,
        name=eth.attributes.name,
        alias=eth.attributes.id,
        description=eth.attributes.desc,
        mac_address=eth.attributes.router_mac,
        admin_status=eth.attributes.admin_st,
    )
    if eth.ethpm_phys_if:
        interface.oper_status = eth.ethpm_phys_if.attributes.oper_st

    return interface


def create_topology_link_metadata(lldp_adj_eps, cdp_adj_eps, device_map, namespace):
    """
    Create a TopologyLinkMetadata object from LLDP or CDP (only LLDP is supported as of right now)
    """
    for lldp_adj_ep in lldp_adj_eps:
        lldp_adj_ep = LldpAdjEp(**lldp_adj_ep.get("lldpAdjEp", {}))
        lldp_attrs = lldp_adj_ep.attributes

        local_device_id = device_map.get(lldp_attrs.local_device_dn)
        local_interface_id = get_interface_dd_id(local_device_id, lldp_attrs.local_port_id)

        local = TopologyLinkSide(
            device=TopologyLinkDevice(dd_id=local_device_id),
            interface=TopologyLinkInterface(
                dd_id=local_interface_id,
                id=lldp_attrs.local_port_id,
                id_type='interface_name',
            ),
        )

        remote_device_dd_id = get_remote_device_dd_id(device_map, lldp_attrs.remote_device_dn, lldp_attrs.mgmt_ip)
        remote_device = TopologyLinkDevice(
            name=lldp_attrs.sys_name,
            description=lldp_attrs.sys_desc,
            id=lldp_attrs.chassis_id_v,
            id_type=lldp_attrs.chassis_id_t,
            ip_address=lldp_attrs.mgmt_ip,
        )
        if remote_device_dd_id:
            remote_device.dd_id = remote_device_dd_id
        remote_interface = TopologyLinkInterface(
            id=lldp_attrs.port_id_v,
            id_type=lldp_attrs.ndm_remote_interface_type,
            description=lldp_attrs.port_desc,
        )
        if remote_device_dd_id:
            remote_interface.dd_id = get_interface_dd_id(remote_device_dd_id, lldp_attrs.remote_port_id)

        remote = TopologyLinkSide(
            device=remote_device,
            interface=remote_interface,
        )

        if remote_device_dd_id:
            link_id = (
                f"{local_device_id}:{get_raw_id(lldp_attrs.local_port_id)}.{get_raw_id(lldp_attrs.remote_port_id)}"
            )
        else:
            link_id = f"{local_device_id}:{get_raw_id(lldp_attrs.local_port_id)}.{lldp_attrs.remote_port_index}"

        yield TopologyLinkMetadata(
            id=link_id,
            source_type=SourceType.LLDP,
            local=local,
            remote=remote,
        )


def get_remote_device_dd_id(device_map, remote_device_dn, mgmt_ip) -> str | None:
    """
    Get the Cisco DN for a remote device, if the device is in the device map then
    check that it matches the management IP of the LLDP neighbor, then return it
    """
    device_id = device_map.get(remote_device_dn, "")
    if device_id:
        if device_id.endswith(mgmt_ip):
            return device_id
    return None


def get_interface_dd_id(device_id: str, port_id: str) -> str:
    """
    Create the interface DD ID based off of the device DD ID and port ID
    ex: default:10.0.200.1:cisco_aci-eth1/1
    """
    raw_id = get_raw_id(port_id)
    return f"{device_id}:{raw_id}"


def get_raw_id(raw_id, raw_id_type="cisco-aci") -> str:
    """
    Create the interface raw ID, based on the type (cisco-aci) and the interface's identifier
    separated by a hyphen - ex: cisco-aci-eth1/1
    """
    return f"{raw_id_type}-{raw_id}"


def get_device_ip_mapping(devices):
    """
    Create a mapping of node ID to device ID
    ex: pod-1-node-1 -> default:10.100.0.1
    """
    devices_map = {}
    for device in devices:
        key = device.pod_node_id
        devices_map[key] = device.id
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
