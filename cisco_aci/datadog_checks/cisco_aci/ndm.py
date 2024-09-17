# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from six import PY3

if PY3:
    from datadog_checks.cisco_aci.models import (
        DeviceMetadata,
        ExporterIPAddressMetadata,
        InterfaceMetadata,
        NetworkDevicesMetadata,
        Node,
        PhysIf,
        TopSystemList,
    )

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


def create_exporter_ip_address_metadata(namespace, top_systems):
    """
    Create an ExporterIPAddressMetadata object from a out-of-band mgmt IP that is available for every device
    """
    top_systems_list = TopSystemList(top_systems=top_systems)
    for top_system in top_systems_list.top_systems:
        yield ExporterIPAddressMetadata(
            device_id=namespace + ":" + top_system.attributes.address,
            exporter_ip_address=top_system.attributes.oob_mgmt_addr,
            prefixlen=top_system.attributes.oob_mgmt_addr_mask,
        )


def get_device_info(device):
    """
    Get device ID and node ID from a device object
    """
    for tag in device.tags:
        if tag.startswith('node_id'):
            node_id = tag.split(':')[1]
            break
    return device.id, node_id


def batch_payloads(namespace, devices, interfaces, exporter_ip_addresses, collect_ts):
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

    for exporter_ip_address in exporter_ip_addresses:
        current_payload, new_payload = append_to_payload(
            exporter_ip_address, network_devices_metadata, namespace, collect_ts
        )
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
