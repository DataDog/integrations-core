# Generic SNMP Metric Packs

This directory contains vendor-agnostic metric packs based on standard SNMP MIBs that can be used across devices from different vendors.

## Structure

```
generic/
└── metric_packs/      # Vendor-agnostic metric definitions
    ├── base.yaml
    ├── bgp.yaml
    ├── interfaces.yaml
    ├── ip.yaml
    ├── ospf.yaml
    ├── tcp.yaml
    └── udp.yaml
```

## Metric Packs

### base.yaml
Basic SNMP system information from SNMPv2-MIB:
- `sysName` - System name
- Device hostname tags

### interfaces.yaml
Standard IF-MIB interface metrics. References the existing `_generic-if.yaml` profile for:
- Interface statistics (octets, packets, errors, discards)
- Interface operational status
- Interface admin status
- Bandwidth utilization

### tcp.yaml
TCP protocol metrics from TCP-MIB. References `_generic-tcp.yaml` for:
- Active connections
- Passive connections
- Connection attempts
- Connection failures
- Segments sent/received

### udp.yaml
UDP protocol metrics from UDP-MIB. References `_generic-udp.yaml` for:
- Datagrams received
- Datagrams sent
- Datagrams with errors
- Port unreachable errors

### ip.yaml
IP protocol metrics from IP-MIB. References `_generic-ip.yaml` for:
- IP forwarding status
- IP datagrams received/sent
- IP fragmentation metrics
- IP routing metrics

### ospf.yaml
OSPF routing protocol metrics from OSPF-MIB. References `_generic-ospf.yaml` for:
- OSPF neighbor states
- OSPF interface metrics
- OSPF area statistics
- LSA counts

### bgp.yaml
BGP routing protocol metrics from BGP4-MIB. References `_generic-bgp4.yaml` for:
- BGP peer states
- BGP received/sent prefixes
- BGP session uptime
- BGP update messages

## Usage in Profiles

These metric packs are referenced using relative paths from vendor-specific profiles:

```yaml
# Example from cisco/profiles/cisco-catalyst.yaml
metric_packs:
  - ../../generic/metric_packs/base
  - ../../generic/metric_packs/interfaces
  - ../../generic/metric_packs/tcp
  - ../../generic/metric_packs/udp
  - ../../generic/metric_packs/ip
  - metadata  # vendor-specific
  - cpu       # vendor-specific
```

## Benefits

1. **Reusability**: Single definition used across all vendors
2. **Consistency**: Same metrics collected from all device types
3. **Maintainability**: Update once, applies everywhere
4. **Standards-Based**: Built on industry-standard MIBs
5. **Vendor-Agnostic**: Works with any SNMP-compliant device

## Standard MIBs Used

- **SNMPv2-MIB** (RFC 3418) - System information
- **IF-MIB** (RFC 2863) - Interface management
- **TCP-MIB** (RFC 4022) - TCP statistics
- **UDP-MIB** (RFC 4113) - UDP statistics
- **IP-MIB** (RFC 4293) - IP statistics
- **OSPF-MIB** (RFC 4750) - OSPF routing
- **BGP4-MIB** (RFC 4273) - BGP routing

## Extending for New Vendors

When creating profiles for a new vendor, start with these generic metric packs and add vendor-specific packs as needed:

```yaml
# Example: hypothetical-vendor/profiles/hypothetical-switch.yaml
device:
  vendor: "hypothetical"

metric_packs:
  - ../../generic/metric_packs/base
  - ../../generic/metric_packs/interfaces
  - ../../generic/metric_packs/tcp
  - ../../generic/metric_packs/udp
  - ../../generic/metric_packs/ip
  - cpu       # vendor-specific CPU metrics
  - memory    # vendor-specific memory metrics
```

