# Cisco Profile to Metric Pack Mapping

This document shows which metric packs are used by each Cisco profile.

## Note on Generic vs Cisco-Specific Metric Packs

Metric packs are divided into two categories:

**Generic Metric Packs** (located in `../generic/metric_packs/`):
- `base`, `interfaces`, `tcp`, `udp`, `ip`, `ospf`, `bgp`
- These use standard MIBs that work across all vendors
- Referenced in profiles using relative path: `../../generic/metric_packs/<name>`

**Cisco-Specific Metric Packs** (located in `metric_packs/`):
- All other metric packs listed below
- These use Cisco proprietary MIBs
- Referenced in profiles by name only: `<name>`

## Profile Mapping Table

| Profile | Generic Packs | Cisco-Specific Packs |
|---------|---------------|---------------------|
| **cisco-catalyst** | base, interfaces, tcp, udp, ip, ospf, bgp | metadata, cpu, memory, environment, fru, entity_sensor, stackwise, catalyst_interfaces, cpu_memory_extended, rtt_monitoring, virtual_switch |
| **cisco-asr** | base, interfaces, tcp, udp, ip, ospf, bgp | metadata, cpu, memory, environment, fru, cpu_memory_extended, rtt_monitoring |
| **cisco-asa** | base, interfaces, tcp, udp, ip | metadata, cpu, memory, firewall, ipsec, remote_access, cpu_memory_extended, entity_sensor |
| **cisco-nexus** | base, interfaces, tcp, udp, ip, ospf, bgp | metadata, cpu, enhanced_memory, entity_sensor, fru |
| **cisco-isr** | base, interfaces, tcp, udp, ip, ospf, bgp | metadata, cpu, memory, environment, fru, cpu_memory_extended |
| **cisco-3850** | base, interfaces, tcp, udp, ip, ospf, bgp | metadata, cpu, memory, environment, fru, entity_sensor, stackwise, catalyst_interfaces, cpu_memory_extended |
| **cisco-catalyst-wlc** | base, interfaces, tcp, udp, ip | metadata, cpu, memory, wireless_controller, environment, fru |
| **cisco-firepower** | base, interfaces, tcp, udp, ip | metadata, cpu, memory, firewall, environment, fru, entity_sensor |
| **cisco-firepower-asa** | base, interfaces, tcp, udp, ip | metadata, cpu, memory, firewall, ipsec, remote_access, environment, fru, entity_sensor |
| **cisco-access-point** | base, interfaces | metadata, cpu, memory |
| **cisco-asa-5525** | base, interfaces, tcp, udp, ip | metadata, cpu, memory, firewall, ipsec, remote_access, cpu_memory_extended |
| **cisco-csr1000v** | base, interfaces, tcp, udp, ip, ospf, bgp | metadata, cpu, memory |
| **cisco-legacy-wlc** | base, interfaces | metadata, cpu, memory, wireless_controller |
| **cisco-load-balancer** | base, interfaces, tcp, udp, ip | metadata, cpu, memory |
| **cisco-sb** | base, interfaces | metadata, cpu, memory |
| **cisco-ucs** | base, interfaces | metadata, cpu, memory, entity_sensor, environment, fru |
| **cisco-wan-optimizer** | base, interfaces, tcp | metadata, cpu, memory |
| **cisco-ise** | base, interfaces | metadata, cpu, memory |
| **cisco-ironport-email** | base, interfaces | metadata, cpu, memory |
| **cisco_icm** | base, interfaces | metadata, cpu, memory, voice |
| **cisco_isr_4431** | base, interfaces, tcp, udp, ip, ospf, bgp | metadata, cpu, memory, environment, fru |
| **cisco_uc_virtual_machine** | base, interfaces | metadata, cpu, memory, voice |
| **cisco** (generic) | base, interfaces, tcp, udp, ip | metadata, cpu, memory |

## Metric Pack Usage Statistics

### Generic Metric Packs
| Metric Pack | Used By # of Profiles | Type |
|-------------|----------------------|------|
| **base** | 23 | Generic (SNMPv2-MIB) |
| **interfaces** | 23 | Generic (IF-MIB) |
| **tcp** | 16 | Generic (TCP-MIB) |
| **udp** | 15 | Generic (UDP-MIB) |
| **ip** | 15 | Generic (IP-MIB) |
| **ospf** | 9 | Generic (OSPF-MIB) |
| **bgp** | 9 | Generic (BGP4-MIB) |

### Cisco-Specific Metric Packs
| Metric Pack | Used By # of Profiles | MIB |
|-------------|----------------------|-----|
| **metadata** | 23 | Cisco-specific |
| **cpu** | 23 | CISCO-PROCESS-MIB |
| **memory** | 22 | CISCO-MEMORY-POOL-MIB |
| **environment** | 9 | CISCO-ENVMON-MIB |
| **fru** | 9 | CISCO-ENTITY-FRU-CONTROL-MIB |
| **entity_sensor** | 7 | CISCO-ENTITY-SENSOR-MIB |
| **cpu_memory_extended** | 6 | CISCO-PROCESS-MIB |
| **firewall** | 4 | CISCO-FIREWALL-MIB |
| **ipsec** | 3 | CISCO-IPSEC-FLOW-MONITOR-MIB |
| **remote_access** | 3 | CISCO-REMOTE-ACCESS-MONITOR-MIB |
| **stackwise** | 2 | CISCO-STACKWISE-MIB |
| **catalyst_interfaces** | 2 | CISCO-IF-EXTENSION-MIB |
| **rtt_monitoring** | 2 | CISCO-RTTMON-MIB |
| **wireless_controller** | 2 | AIRESPACE-WIRELESS-MIB |
| **voice** | 2 | CISCO-CCM-MIB, CISCO-VOICE-DIAL-CONTROL-MIB |
| **enhanced_memory** | 1 | CISCO-ENHANCED-MEMPOOL-MIB |
| **virtual_switch** | 1 | CISCO-VIRTUAL-SWITCH-MIB |

## Device Type Categories

### Switches
- cisco-catalyst
- cisco-3850
- cisco-nexus
- cisco-sb

### Routers
- cisco-asr
- cisco-isr
- cisco-csr1000v
- cisco_isr_4431

### Firewalls
- cisco-asa
- cisco-asa-5525
- cisco-firepower
- cisco-firepower-asa

### Wireless
- cisco-catalyst-wlc
- cisco-legacy-wlc
- cisco-access-point

### Specialized
- cisco-ucs (servers)
- cisco-load-balancer
- cisco-wan-optimizer
- cisco-ise (security)
- cisco-ironport-email (email security)
- cisco_icm (contact center)
- cisco_uc_virtual_machine (unified communications)
- cisco (generic fallback)

## Standard MIBs Reference

### Generic Metric Packs (Standard MIBs)
- **SNMPv2-MIB** (RFC 3418) - System information (`base`)
- **IF-MIB** (RFC 2863) - Interface management (`interfaces`)
- **TCP-MIB** (RFC 4022) - TCP statistics (`tcp`)
- **UDP-MIB** (RFC 4113) - UDP statistics (`udp`)
- **IP-MIB** (RFC 4293) - IP statistics (`ip`)
- **OSPF-MIB** (RFC 4750) - OSPF routing (`ospf`)
- **BGP4-MIB** (RFC 4273) - BGP routing (`bgp`)

### Cisco Proprietary MIBs
All other metric packs use Cisco-specific MIBs as listed in the table above.
