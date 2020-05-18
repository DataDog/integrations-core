# Introduction to SNMP

In this introduction, we'll cover general information about the SNMP protocol, including key concepts such as OIDs and MIBs.

If you're already familiar with the SNMP protocol, feel free to skip to the next page.

## What is SNMP?

### Overview

SNMP (Simple Network Management Protocol) is a protocol for monitoring [network devices](https://en.wikipedia.org/wiki/Networking_hardware). It uses UDP and supports both a request/response model (commands and queries) and a notification model (traps, informs).

In the request/response model, the **SNMP manager** (eg. the Datadog Agent) issues an **SNMP command** (`GET`, `GETNEXT`, `BULK`) to an **SNMP agent** (eg. a network device).

SNMP was born in the 1980s, so it has been around for a long time. While more modern alternatives like [NETCONF](https://en.wikipedia.org/wiki/NETCONF) and [OpenConfig](https://github.com/openconfig) have been gaining attention, a large amount of network devices still use SNMP as their primary monitoring interface.

### SNMP versions

The SNMP protocol exists in 3 versions: `v1` (legacy), `v2c`, and `v3`.

The main differences between v1/v2c and v3 are the authentication mechanism and transport layer, as summarized below.

| Version | Authentication                    | Transport layer                           |
| ------- | --------------------------------- | ----------------------------------------- |
| v1/v2c  | Password (the _community string_) | Plain text only                           |
| v3      | Username/password                 | Support for packet signing and encryption |

## OIDs

### What is an OID?

**Identifiers for queryable quantities**

An **OID**, also known as an **Object Identifier**, is an identifier for a quantity ("object") that can be retrieved from an SNMP device. Such quantities may include uptime, temperature, network traffic, etc (quantities available will vary across devices).

To make them processable by machines, OIDs are represented as dot-separated sequences of numbers, e.g. `1.3.6.1.2.1.1.1`.

**Global definition**

OIDs are **globally defined**, which means they have the same meaning regardless of the device that processes the SNMP query. For example, querying the `1.3.6.1.2.1.1.1` OID (also known as `sysDescr`) on _any_ SNMP agent will make it return the system description. (More on the OID/label mapping can be found in the [MIBs](#mibs) section below.)

**Not all OIDs contain metrics data**

OIDs can refer to various types of objects, such as strings, numbers, tables, etc.

In particular, this means that only a fraction of OIDs refer to numerical quantities that can actually be sent as metrics to Datadog. However, non-numerical OIDs can also be useful, especially for tagging.

### The OID tree

OIDs are structured in a tree-like fashion. Each number in the OID represents a node in the tree.

The wildcard notation is often used to refer to a sub-tree of OIDs, e.g. `1.3.6.1.2.*`.

It so happens that there are two main OID sub-trees: a sub-tree for general-purpose OIDs, and a sub-tree for vendor-specific OIDs.

#### Generic OIDs

Located under the sub-tree: `1.3.6.1.2.1.*` (a.k.a.`SNMPv2-MIB` or `mib-2`).

These OIDs are applicable to all kinds of network devices (although all devices may not expose all OIDs in this sub-tree).

For example, `1.3.6.1.2.1.1.1` corresponds to `sysDescr`, which contains a free-form, human-readable description of the device.

#### Vendor-specific OIDs

Located under the sub-tree: `1.3.6.1.4.1.*` (a.k.a. `enterprises`).

These OIDs are defined and managed by network device vendors themselves.

Each vendor is assigned its own enterprise sub-tree in the form of `1.3.6.1.4.1.<N>.*`.

For example:

- `1.3.6.1.4.1.2.*` is the sub-tree for IBM-specific OIDs.
- `1.3.6.1.4.1.9.*` is the sub-tree for Cisco-specific OIDs.

The full list of vendor sub-trees can be found here: [SNMP OID 1.3.6.1.4.1](http://cric.grenoble.cnrs.fr/Administrateurs/Outils/MIBS/?oid=1.3.6.1.4.1).

### Notable OIDs

| OID               | Label               | Description                                                                                    |
| ----------------- | ------------------- | ---------------------------------------------------------------------------------------------- |
| `1.3.6.1.2.1.2`   | `sysObjectId`       | An OID whose value is an OID that represents the device make and model (yes, it's a bit meta). |
| `1.3.6.1.2.1.1.1` | `sysDescr`          | A human-readable, free-form description of the device.                                         |
| `1.3.6.1.2.1.1.3` | `sysUpTimeInstance` | The device uptime.                                                                             |

## MIBs

### What is an MIB?

OIDs are grouped in modules called **MIBs** (Management Information Base). An MIB describes the hierarchy of a given set of OIDs. (This is somewhat analogous to a dictionary that contains the definitions for each word in a spoken language.)

For example, the [`IF-MIB`](http://cric.grenoble.cnrs.fr/Administrateurs/Outils/MIBS/?module=IF-MIB) describes the hierarchy of OIDs within the sub-tree `1.3.6.1.2.1.2.*`. These OIDs contain metrics about the network interfaces available on the device. (Note how its location under the `1.3.6.1.2.*` sub-tree indicates that it is a generic MIB, available on most network devices.)

As part of the description of OIDs, an MIB defines a human-readable **label** for each OID. For example, `IF-MIB` describes the OID `1.3.6.1.2.1.1` and assigns it the label `sysDescr`. The operation that consists in finding the OID from a label is called **OID resolution**.

### Tools and resources

The following resources can be useful when working with MIBs:

- [MIB Discovery](http://cric.grenoble.cnrs.fr/Administrateurs/Outils/MIBS/): a search engine for OIDs. Use it to find what an OID corresponds to, which MIB it comes from, what label it is known as, etc.
- [Circitor MIB files repository](http://circitor.fr/Mibs/Mibs.php): a repository and search engine where one can download actual `.mib` files.
- [SNMP Labs MIB repository](http://mibs.snmplabs.com/asn1/): alternate repo of many common MIBs. **Note**: this site hosts the underlying MIBs which the `pysnmp-mibs` library (used by the SNMP Python check) actually validates against. Double check any MIB you get from an alternate source with what is in this repo.

## Learn more

For other high-level overviews of SNMP, see:

- [How SNMP Works (Youtube)](https://www.youtube.com/watch?v=2IXP0TkwNJU)
- [SNMP (Wikipedia)](https://en.wikipedia.org/wiki/Simple_Network_Management_Protocol)
