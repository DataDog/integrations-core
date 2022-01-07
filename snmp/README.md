# SNMP Check

## Overview

Simple Network Management Protocol (SNMP) is a standard for monitoring network-connected devices, such as routers, switches, servers, and firewalls. It uses UDP and supports both a request and response model and a notification model.

In the request and response model, the Datadog Agent issues an SNMP command, such as `GET`, `GETNEXT`, or `BULK`, to a network device. The SNMP check collects SNMP metrics from your network devices.

SNMP uses sysObjectIDs (System Object Identifiers) to uniquely identify devices, and OIDs (Object Identifiers) to uniquely identify managed objects.

### Object identifiers

An OID is an identifier for a quantity, such as uptime, temperature, or network traffic, that can be retrieved from an SNMP device. OIDs follow a hierarchical tree pattern: under the root is ISO, which is numbered 1. The next level is ORG and numbered 3 and so on. Each level is separated by a `.`.

OIDs are globally defined, which means they have the same meaning regardless of the device that processes the SNMP query. OIDs can refer to various types of objects, such as strings, numbers, tables, etc. This means that only a fraction of OIDs refer to numerical quantities that can be sent as metrics to Datadog. However, non-numerical OIDs can also be useful, especially for [tagging][3].

#### Generic object identifiers

The wildcard notation is often used to refer to a sub-tree of OIDs, for example: `1.3.6.1.2.*`. These OIDs are applicable to all kinds of network devices, although all devices may not expose all OIDs in this sub-tree.

For example, `1.3.6.1.2.1.1.1` corresponds to `sysDescr`, which contains a free-form, human-readable description of the device.

#### Vendor-specific object identifiers

Vendor-specific OIDs are located under the sub-tree `1.3.6.1.4.1.*`, also known as enterprises.

These OIDs are defined and managed by network device vendors themselves. Each vendor is assigned its own enterprise sub-tree in the form of `1.3.6.1.4.1.<N>.*`.

For example, `1.3.6.1.4.1.2.*` is the sub-tree for IBM-specific OIDs. `1.3.6.1.4.1.9.*` is the sub-tree for Cisco-specific OIDs. The full list of vendor sub-trees can be found under: [SNMP OID 1.3.6.1.4.1][4].

### Management information base

OIDs are grouped in modules called MIBs (Management information base). A MIB acts as a translator between OIDs and human readable names, and organizes a subset of the hierarchy. For example, IF-MIB describes the OID 1.3.6.1.2.1.1 and assigns it the label sysDescr. The operation that consists in finding the OID from a label is called OID resolution. The IF-MIB describes the hierarchy of OIDs within the sub-tree `1.3.6.1.2.1.2.*`. These OIDs contain metrics about the network interfaces available on the device. **Note**: Its location under the `1.3.6.1.2.*` sub-tree indicates that it is a generic MIB, available on most network devices.

Because of the way the tree is structured, most SNMP values start with the same set of objects:

* `1.3.6.1.1`: (MIB-II) A standard that holds system information like uptime, interfaces, and network stack.
* `1.3.6.1.4.1`: A standard that holds vendor specific information.

## Setup

To install and configure the SNMP integration, see the [Network Device Monitoring][1] documentation.

## Further Reading

Additional helpful documentation, links, and articles:

* [Monitor SNMP with Datadog][2]

[1]: https://docs.datadoghq.com/network_performance_monitoring/devices/setup
[2]: https://www.datadoghq.com/blog/monitor-snmp-with-datadog/
[3]: https://docs.datadoghq.com/getting_started/tagging/
[4]: http://cric.grenoble.cnrs.fr/Administrateurs/Outils/MIBS/?oid=1.3.6.1.4.1