# Cisco SNMP Profiles and Metric Packs

This directory contains the reorganized Cisco SNMP profiles using the new **metric packs** architecture.

## Structure

```
cisco/
├── metric_packs/      # Cisco-specific metric groupings
│   ├── metadata.yaml
│   ├── cpu.yaml
│   ├── memory.yaml
│   ├── environment.yaml
│   ├── fru.yaml
│   ├── entity_sensor.yaml
│   ├── stackwise.yaml
│   ├── firewall.yaml
│   ├── ipsec.yaml
│   ├── remote_access.yaml
│   ├── rtt_monitoring.yaml
│   ├── virtual_switch.yaml
│   ├── wireless_controller.yaml
│   ├── voice.yaml
│   ├── catalyst_interfaces.yaml
│   ├── cpu_memory_extended.yaml
│   └── enhanced_memory.yaml
│
└── profiles/          # Device profiles referencing metric packs
    ├── cisco-catalyst.yaml
    ├── cisco-asr.yaml
    ├── cisco-asa.yaml
    ├── cisco-nexus.yaml
    ├── cisco-isr.yaml
    ├── cisco-3850.yaml
    ├── cisco-catalyst-wlc.yaml
    ├── cisco-firepower.yaml
    ├── cisco-firepower-asa.yaml
    ├── cisco-access-point.yaml
    ├── cisco-asa-5525.yaml
    ├── cisco-csr1000v.yaml
    ├── cisco-legacy-wlc.yaml
    ├── cisco-load-balancer.yaml
    ├── cisco-sb.yaml
    ├── cisco-ucs.yaml
    ├── cisco-wan-optimizer.yaml
    ├── cisco-ise.yaml
    ├── cisco-ironport-email.yaml
    ├── cisco_icm.yaml
    ├── cisco_isr_4431.yaml
    ├── cisco_uc_virtual_machine.yaml
    └── cisco.yaml
```

## Metric Packs

Metric packs are logical groupings of OIDs/metrics that are typically enabled or disabled together. Each metric pack is a small YAML file containing related metrics.

### Generic Metric Packs (Vendor-Agnostic)

The following metric packs are located in `../generic/metric_packs/` and use standard MIBs that work across vendors:

- **base**: Basic SNMP system information (sysName, device_hostname) - SNMPv2-MIB
- **interfaces**: Standard IF-MIB interface metrics
- **tcp**: TCP protocol metrics - TCP-MIB
- **udp**: UDP protocol metrics - UDP-MIB
- **ip**: IP protocol metrics - IP-MIB
- **ospf**: OSPF routing protocol - OSPF-MIB
- **bgp**: BGP routing protocol - BGP4-MIB

### Cisco-Specific Metric Packs

The following metric packs use Cisco proprietary MIBs:

- **metadata**: Device metadata (vendor, version, model, os_name)
- **cpu**: CPU utilization metrics - CISCO-PROCESS-MIB
- **memory**: Memory usage metrics - CISCO-MEMORY-POOL-MIB

#### Hardware Monitoring

- **environment**: Temperature, fan, and power supply monitoring - CISCO-ENVMON-MIB
- **fru**: Field Replaceable Unit status - CISCO-ENTITY-FRU-CONTROL-MIB
- **entity_sensor**: Entity sensor metrics (Catalyst, Nexus) - CISCO-ENTITY-SENSOR-MIB
- **stackwise**: StackWise metrics for stacked switches - CISCO-STACKWISE-MIB
- **catalyst_interfaces**: Catalyst-specific interface extensions - CISCO-IF-EXTENSION-MIB
- **cpu_memory_extended**: Extended CPU and memory metrics - CISCO-PROCESS-MIB
- **enhanced_memory**: Enhanced memory MIB (Nexus) - CISCO-ENHANCED-MEMPOOL-MIB

#### Security

- **firewall**: Firewall connection statistics - CISCO-FIREWALL-MIB
- **ipsec**: IPSec VPN tunnel metrics - CISCO-IPSEC-FLOW-MONITOR-MIB
- **remote_access**: Remote access VPN sessions - CISCO-REMOTE-ACCESS-MONITOR-MIB

#### Specialized

- **wireless_controller**: WLC access point metrics - AIRESPACE-WIRELESS-MIB
- **voice**: VoIP/UCaaS metrics - CISCO-CCM-MIB, CISCO-VOICE-DIAL-CONTROL-MIB
- **rtt_monitoring**: Round-trip time monitoring - CISCO-RTTMON-MIB
- **virtual_switch**: Virtual Switching System metrics - CISCO-VIRTUAL-SWITCH-MIB

## Profiles

Each profile represents a specific Cisco device type and references the appropriate metric packs. Profiles include:

- **Device metadata**: Vendor, type
- **Metric packs list**: References to metric pack names
- **sysObjectID list**: OIDs to match devices

### Example Profile

```yaml
# cisco-catalyst.yaml
device:
  vendor: "cisco"

metadata:
  device:
    fields:
      type:
        value: "switch"

metric_packs:
  - ../../generic/metric_packs/base       # Generic
  - ../../generic/metric_packs/interfaces # Generic
  - metadata                              # Cisco-specific
  - cpu                                   # Cisco-specific
  - memory                                # Cisco-specific
  - environment                           # Cisco-specific
  - stackwise                             # Cisco-specific

sysobjectid:
  - 1.3.6.1.4.1.9.1.696  # catalyst2960G24
  - 1.3.6.1.4.1.9.1.1641 # cat385048P
```

## Benefits of Metric Packs

1. **Modularity**: Metrics are organized by function
2. **Reusability**: Common metric packs shared across profiles
3. **User Control**: Users can enable/disable logical groups
4. **Maintainability**: Easier to update specific metric groups
5. **Discoverability**: Clear naming shows what each pack does

## Usage

When a device is discovered, the SNMP integration:
1. Matches the device's sysObjectID to a profile
2. Loads all metric packs referenced in that profile
3. Collects metrics from the enabled metric packs

Metric packs are never enabled by default on their own - they must be referenced by a profile.

