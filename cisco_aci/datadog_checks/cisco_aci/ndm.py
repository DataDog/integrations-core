# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import ipaddress

from six import PY3

if PY3:
    from datadog_checks.cisco_aci.models import (
        DeviceMetadata,
        InterfaceMetadata,
        IPAddressMetadata,
        NetflowExporterPol,
        NetworkDevicesMetadata,
        Node,
        PhysIf,
    )
else:
    DeviceMetadata = None
    Eth = None
    InterfaceMetadata = None
    Node = None

from . import helpers

VENDOR_CISCO = 'cisco'
PAYLOAD_METADATA_BATCH_SIZE = 100


def create_node_metadata(node_attrs, tags, namespace):
    """
    Create a DeviceMetadata object from a node's attributes
    """
    node = Node(attributes=node_attrs)
    hostname = helpers.get_hostname_from_dn(node.attributes.dn)
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


def create_ip_address_metadata(netflow_pols, devices):
    """
    Create an IPAddressMetadata object from a netflow exporter policy
    """
    src_addresses = []
    for pol in netflow_pols:
        netflow_exporter_pol = pol.get('netflowExporterPol', {})
        nep = NetflowExporterPol(attributes=netflow_exporter_pol.get('attributes', {}))
        src_addresses.append(nep.attributes.src_address)

    devices_list = [get_device_info(d) for d in devices]

    for device_id, node_id in devices_list:
        for src_address in src_addresses:
            device_export_ip, max_prefixlen = get_node_exporter_ip(node_id, src_address)
            ip_address_meta = IPAddressMetadata(
                device_id=device_id, ip_address=device_export_ip, prefix_len=max_prefixlen
            )
            yield ip_address_meta


def get_device_info(device):
    """
    Get device ID and node ID from a device object
    """
    for tag in device.tags:
        if tag.startswith('node_id'):
            node_id = tag.split(':')[1]
            break
    return device.id, node_id


def get_node_exporter_ip(node_id, src_address):
    """
    Get the IP address for a specific node from the source address
    """
    try:
        network = ipaddress.ip_network(src_address)
    except ValueError as e:
        raise ValueError("Invalid IP address / network mask: {}".format(e))

    # check if host number is within valid range
    if int(node_id) > network.num_addresses:
        raise ValueError("Node ID is out of range for the given network {}".format(src_address))

    host_address = network.network_address + int(node_id)
    return format(host_address), str(host_address.max_prefixlen)


def batch_payloads(namespace, devices, interfaces, ip_addresses, collect_ts):
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

    for ip_address in ip_addresses:
        current_payload, new_payload = append_to_payload(ip_address, network_devices_metadata, namespace, collect_ts)
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
