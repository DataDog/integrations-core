# SNMP Check

## Overview

Simple Network Management Protocol (SNMP) is a standard for monitoring network-connected devices, such as routers, switches, servers, and firewalls. This check collects SNMP metrics from your network devices.

SNMP uses sysOIDs (System Object Identifiers) to uniquely identify devices, and OIDs (Object Identifiers) to uniquely identify managed objects. OIDs follow a hierarchical tree pattern: under the root is ISO which is numbered 1, then next level is ORG and numbered 3 and so on, with each level being separated by a `.`

A MIB (Management Information Base) acts as a translator between OIDs and human readable names, and organizes a subset of the hierarchy. Because of the way the tree is structured, most SNMP values start with the same set of objects: 1.3.6.1.1 for MIB-II which is a standard that holds system information like uptime, interfaces, network stack, and 1.3.6.1.4.1 which holds vendor specific information.

## Setup
### Installation

The SNMP check is included in the [Datadog Agent][1] package.

### Configuration

_Note: The following features are in beta._

Datadog's SNMP integration scans a provided subnet, auto discovers network devices and collects metrics using Datadog's sysOID mapped device profiles. Configuration for the integration check for the subnet to scan, snmp version to use, and profiles should ben defined in the `snmp.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample snmp.d/conf.yaml][3] for all available configuration options.

#### Configuring Auto-Discovery

1. Install/upgrade the Datadog Agent to v6.16.

   You must be on v6.15+ of the Datadog Agent to enable this feature.

   If you already have a Datadog Agent installed, and would like to upgrade to Agent v6, a script is available to automatically install or upgrade to the new agent.

   For platform specific instructions, and more information about upgrading the Datadog Agent, see the Datadog docs

1. Configure the SNMP integration check with [snmp.d/conf.yaml][17] -- see samples included below. Define the following parameters in the yaml for the SNMP check:

  | Parameter Name | Definition | Is required for autodiscovery | Default value | Example |
  | --- |  --- | --- | --- | --- |  
  | `profiles` | The profiles you want the Datadog Agent to use. A profile is a collection of OIDs, the datadog Agent will poll and collect metrics and their associated tags from. A complete list of Datadog supported profiles can be found in the Datadog [integrations-core repo][18]. Profiles can either be referenced by file, under `definition_file`, or be written inline under `definition`. Any of the OOTB Datadog profiles can be listed by their name. If there are additional profiles that you already have written -- please let me know, we’d love to add them to our open source repo -- can be referenced by the file path. Also note, the generic profile is currently listed as `generic_router.yaml`, but this should work for both routers, switches etc. | Yes | - | |
  | `network_address`| The subnet and mask the Agent will scan and discover devices on. Should be written in ipv4 notation. | Yes | - | `network_address:192.168.100.14/24`|
  | `community_string` | For use with SNMPv1 and SNMPv2 | No | | |
  | `snmp_version` | The SNMP version you are using.| No | 2 | |
  | `port` | The pot the Datadog agent will be listening on. | No | 161 | |
  | `timeout` | The number of seconds before timing out | No | 1 | | |
  | `retries` | The number of retries before failure. | No | 5 | |
  | `discovery_interval`| The interval between discovery scans. | No | 3600s | |
  | `discovery_allowed_failures` | The number of times a discovered host can fail before being removed from the list of discovered devices. | No | 3 | |
  | `bulk_threshold` | The number of symbols in a table that triggers a BULK request. this param is only relevant for SNMPv > 1. | No | 5 | |
  | `tags` | A list of global tags to add to every metric. Read more about [tagging in Datadog][19]. | No | - | `tags: - firewall` |

#### Sample config
```
init_config:
  @param profiles - object - optional
  profiles:
    f5-big-ip:
      definition_file: f5-big-ip.yaml
    router:
      definition_file: generic-router.yaml

instances:  
   ## @param network_address - string - optional
   network_address: <NETWORK_ADDRESS>

   ## @param port - integer - optional - default: 161
   port: 161

   ## @param community_string - string - optional
   community_string: public

   ## @param snmp_version - integer - optional - default: 2
   snmp_version: 2

   ## @param timeout - integer - optional - default: 1
   timeout: 1

   ## @param retries - integer - optional - default: 5
   retries: 5

   ## @param discovery_interval - integer - optional - default: 3600
   discovery_interval: 3600

   ## @param discovery_allowed_failures - integer - optional - default: 3
   discovery_allowed_failures: 3

   ## @param enforce_mib_constraints - boolean - optional - default: true
   enforce_mib_constraints: true

   ## @param bulk_threshold - integer - optional - default: 5
   bulk_threshold: 5

   ## @param tags - list of key:value element - optional
   tags:
      - <KEY_1>:<VALUE_1>
      - <KEY_2>:<VALUE_2>
```



##### sysOID mapped device profiles

Profiles allow the SNMP check to reuse metric definitions across several device types, or instances. Profiles define metrics the same way as instances, either inline in the configuration file or in separate files. Each instance can only match a single profile. For example, you can define a profile in the `init_config` section:

```yaml
init_config:
  profiles:
    my-profile:
      definition:
        - MIB: IP-MIB
          table: ipSystemStatsTable
          symbols:
            - ipSystemStatsInReceives
          metric_tags:
            - tag: ipversion
          index: 1
      sysobjectid: '1.3.6.1.4.1.8072.3.2.10'
```

Then either reference it explicitly by name, or use sysObjectID detection:

```
yaml
instances:
   - ip_address: 192.168.34.10
     profile: my-profile
   - ip_address: 192.168.34.11
     # Don't need anything else here, the check will query the sysObjectID
     # and use the profile if it matches.
```

If necessary, additional metrics can be defined in the instances. These metrics are collected alongside those in the profile

#### Metric definition by Profile
Profiles can be used interchangeably, such that devices that share MIB dependencies can reuse the same profiles. For example, the Cisco c3850 profile can be used across many Cisco Switches.

Please note: Profiles currently require there to a local version of the MIBs referenced.

##### [Generic Router Profile][20]

MIBs needed for local reference: IF-MIB, IP-MIB, TCP-MIB, UDP-MIB

| symbol | definition | tags |
| --- | --- | --- |
| `snmp.ifInDiscards` | The number of inbound packets which were chosen to be discarded even though no errors had been detected to prevent their being deliverable to a higher-layer protocol. | `interface` |
| `snmp.ifOutErrors` | The number of outbound packets that could not be transmitted because of errors. | `interface` |
|` snmp.ifOutDiscards` | The number of outbound packets which were chosen to be discarded even though no errors had been detected to prevent their being transmitted.|  `interface` |
| `snmp.ifInErrors` | The number of inbound packets that contained errors preventing them from being deliverable to a higher-layer protocol. | `interface`|
| `snmp.ifAdminStatus` | The desired state of the interface. | `interface`|
| `snmp.ifOperStatus` | The current operational state of the interface. | `interface`
| `snmp.ifHCInOctets` | The total number of octets received on the interface, including framing characters. | `interface`|
| `snmp.ifHCInUcastPkts` | The number of packets, delivered by this sub-layer to a higher (sub-)layer, which were not addressed to a multicast or broadcast address at this sub-layer. | `interface`|
| `snmp.ifHCInBroadcastPkts` | The number of packets, delivered by this sub-layer to a higher (sub-)layer, which were addressed to a broadcast address at this sub-layer. | `interface`|
| `snmp.ifHCOutOctets` | The total number of octets transmitted out of the interface, including framing characters.| `interface`
| `snmp.ifHCOutUcastPkts` | The total number of packets that higher-level protocols requested be transmitted, and which were not addressed to a multicast or broadcast address at this sub-layer, including those that were discarded or not sent.| `interface`
| `snmp.ifHCOutMulticastPkts` | The total number of packets that higher-level protocols requested be transmitted, and which were addressed to a multicast address at this sub-layer, including those that were discarded or not sent. | `interface`
| `snmp.ifHCOutBroadcastPkts` | The total number of packets that higher-level protocols requested be transmitted, and which were addressed to a broadcast address at this sub-layer, including those that were discarded or not sent.| `interface`
| `snmp.ipSystemStatsHCInReceives` | The total number of input IP datagrams received, including those received in error.| `ipversion`
| `snmp.ipSystemStatsHCInOctets` | The total number of octets received in input IP datagrams,including those received in error. | `ipversion`
| `snmp.ipSystemStatsInHdrErrors` | The number of input IP datagrams discarded due to errors in their IP headers, including version number mismatch, other their IP headers, including version number mismatch, other format errors, hop count exceeded, errors discovered in processing their IP options, etc. | `ipversion`
| `snmp.ipSystemStatsInNoRoutes` |  The number of input IP datagrams discarded because no route could be found to transmit them to their destination. | `ipversion`
| `snmp.ipSystemStatsInAddrErrors` | The number of input IP datagrams discarded because the IP address in their IP header's destination field was not a valid address to be received at this entity. | `ipversion`
| `snmp.ipSystemStatsInUnknownProtos` | The number of locally-addressed IP datagrams received successfully but discarded because of an unknown or unsupported protocol. | `ipversion`
| `snmp.ipSystemStatsInTruncatedPkts` | The number of input IP datagrams discarded because the datagram frame didn't carry enough data. | `ipversion`
| `snmp.ipSystemStatsHCInForwDatagrams` | The number of input datagrams for which this entity was not their final IP destination and for which this entity attempted to find a route to forward them to that final destination. | `ipversion`
| `snmp.ipSystemStatsReasmReqds` | The number of IP fragments received that needed to be reassembled at this interface. | `ipversion`
| `snmp.ipSystemStatsReasmOKs` | The number of IP datagrams successfully reassembled. | `ipversion`
| `snmp.ipSystemStatsReasmFails` | The number of failures detected by the IP re-assembly algorithm (for whatever reason: timed out, errors, etc.). | `ipversion`
| `snmp.ipSystemStatsInDiscards` | The number of input IP datagrams for which no problems were encountered to prevent their continued processing, but were discarded (e.g, for lack of buffer space). | `ipversion`
|` snmp.ipSystemStatsHCInDelivers` | The total number of datagrams successfully delivered to IP user-protocols (including ICMP). | `ipversion`
| `snmp.ipSystemStatsHCOutRequests` | The total number of IP datagrams that local IP user-protocols (including ICMP) supplied to IP in requests for transmission. | `ipversion`
| `snmp.ipSystemStatsOutNoRoutes` | The number of locally generated IP datagrams discarded because no route could be found to transmit them to their destination. | `ipversion`
| `snmp.ipSystemStatsHCOutForwDatagrams` | The number of datagrams for which this entity was not their final IP destination and for which it was successful in finding a path to their final destination. | `ipversion`
| `snmp.ipSystemStatsOutDiscards` | The number of output IP datagrams for which no problem was encountered to prevent their transmission to their destination, but were discarded (e.g., for lack of buffer space). | `ipversion`
| `snmp.ipSystemStatsOutFragReqds` | The number of IP datagrams that would require fragmentation in order to be transmitted. | `ipversion`
| `snmp.ipSystemStatsOutFragOKs` | The number of IP datagrams that have been successfully  fragmented. | `ipversion`
| `snmp.ipSystemStatsOutFragFails` | The number of IP datagrams that have been discarded because they needed to be fragmented but could not be. |`ipversion`
| `snmp.ipSystemStatsOutFragCreates` | The number of output datagram fragments that have been generated as a result of IP fragmentation. |`ipversion`
| `snmp.ipSystemStatsHCOutTransmits` | The total number of IP datagrams that this entity supplied to the lower layers for transmission. | `ipversion`
| `snmp.ipSystemStatsHCOutOctets` | The total number of octets in IP datagrams delivered to the lower layers for transmission. | `ipversion`
| `snmp.ipSystemStatsHCInMcastPkts` | The number of IP multicast datagrams received. |`ipversion`
| `snmp.ipSystemStatsHCInMcastOctets` | The total number of octets received in IP multicast datagrams. | `ipversion`
| `snmp.ipSystemStatsHCOutMcastPkts` | The number of IP multicast datagrams transmitted. |`ipversion`
| `snmp.ipSystemStatsHCOutMcastOctets` | The total number of octets transmitted in IP multicast datagrams.| `ipversion`
| `snmp.ipSystemStatsHCInBcastPkts` | The number of IP broadcast datagrams received.| `ipversion`
| `snmp.ipSystemStatsHCOutBcastPkts` | The number of IP broadcast datagrams transmitted. | `ipversion`
| `snmp.ipIfStatsHCInOctets` | The total number of octets received in input IP datagrams, including those received in error. | `ipversion`, `interface` |
| `snmp.ipIfStatsInHdrErrors` | The number of input IP datagrams discarded due to errors in their IP headers, including version number mismatch, other format errors, hop count exceeded, errors discovered in processing their IP options, etc. | `ipversion`, `interface` |
| `snmp.ipIfStatsInNoRoutes` |The number of input IP datagrams discarded because no route could be found to transmit them to their destination. | `ipversion`, `interface` |
| `snmp.ipIfStatsInAddrErrors` | The number of input IP datagrams discarded because the IP address in their IP header's destination field was not a valid address to be received at this entity. | `ipversion`, `interface` |
| `snmp.ipIfStatsInUnknownProtos` | The number of locally-addressed IP datagrams received successfully but discarded because of an unknown or unsupported protocol. | `ipversion`, `interface` |
| `snmp.ipIfStatsInTruncatedPkts` | The number of input IP datagrams discarded because the datagram frame didn't carry enough data. | `ipversion`, `interface` |
| `snmp.ipIfStatsHCInForwDatagrams` | The number of input datagrams for which this entity was not their final IP destination and for which this entity attempted to find a route to forward them to that final destination. | `ipversion`, `interface` |
| `snmp.ipIfStatsReasmReqds` | The number of IP fragments received that needed to be reassembled at this interface. | `ipversion`, `interface` |
| `snmp.ipIfStatsReasmOKs` | The number of IP datagrams successfully reassembled. | `ipversion`, `interface` |
| `snmp.ipIfStatsReasmFails` | The number of failures detected by the IP re-assembly algorithm (for whatever reason: timed out, errors, etc.). | `ipversion`, `interface` |
| `snmp.ipIfStatsInDiscards` | The number of input IP datagrams for which no problems were encountered to prevent their continued processing, but were discarded (e.g., for lack of buffer space). | `ipversion`, `interface` |
| `snmp.ipIfStatsHCInDelivers` | The total number of datagrams successfully delivered to IP user-protocols (including ICMP). | `ipversion`, `interface` |
| `snmp.ipIfStatsHCOutRequests` | The total number of IP datagrams that local IP user-protocols (including ICMP) supplied to IP in requests for transmission. | `ipversion`, `interface` |
| `snmp.ipIfStatsHCOutForwDatagrams` | The number of datagrams for which this entity was not their final IP destination and for which it was successful in finding a path to their final destination. | `ipversion`, `interface` |
| `snmp.ipIfStatsOutDiscards` | The number of output IP datagrams for which no problem was encountered to prevent their transmission to their destination, but were discarded (e.g., for lack of buffer space). | `ipversion`, `interface` |
| `snmp.ipIfStatsOutFragReqds` | The number of IP datagrams that would require fragmentation in order to be transmitted. | `ipversion`, `interface` |
| `snmp.ipIfStatsOutFragOKs` | The number of IP datagrams that have been successfully fragmented. | `ipversion`, `interface` |
| `snmp.ipIfStatsOutFragFails` | The number of IP datagrams that have been discarded because they needed to be fragmented but could not be. | `ipversion`, `interface` |
| `snmp.ipIfStatsOutFragCreates` | The number of output datagram fragments that have been generated as a result of IP fragmentation. | `ipversion`, `interface` |
| `snmp.ipIfStatsHCOutTransmits` | The total number of IP datagrams that this entity supplied to the lower layers for transmission. | `ipversion`, `interface` |
| `snmp.ipIfStatsHCOutOctets` | The total number of octets in IP datagrams delivered to the lower layers for transmission. | `ipversion`, `interface` |
| `snmp.ipIfStatsHCInMcastPkts` | The number of IP multicast datagrams received. | `ipversion`, `interface` |
| `snmp.ipIfStatsHCInMcastOctets` | The total number of octets received in IP multicast datagrams. | `ipversion`, `interface` |
| `snmp.ipIfStatsHCOutMcastPkts` | The number of IP multicast datagrams received.  | `ipversion`, `interface` |
| `snmp.ipIfStatsHCOutMcastOctets` | The total number of octets transmitted in IP multicast datagrams. | `ipversion`, `interface` |
| `snmp.ipIfStatsHCInBcastPkt`s | The number of IP broadcast datagrams received. | `ipversion`, `interface` |
| `snmp.ipIfStatsHCOutBcastPkts` | The number of IP broadcast datagrams transmitted. | `ipversion`, `interface` |
| `snmp.tcpActiveOpens` | The number of times that TCP connections have made a direct transition to the SYN-SENT state from the CLOSED state. |  |
| `snmp.tcpPassiveOpens` | The number of times TCP connections have made a direct transition to the SYN-RCVD state from the LISTEN state. | |
| `snmp.tcpAttemptFails` | The number of times that TCP connections have made a direct transition to the CLOSED state from either the SYN-SENT state or the SYN-RCVD state, plus the number of times that TCP connections have made a direct transition to the LISTEN state from the SYN-RCVD state. | |
| `snmp.tcpEstabResets` | The number of times that TCP connections have made a direct transition to the CLOSED state from either the ESTABLISHED state or the CLOSE-WAIT state. | |
| `snmp.tcpCurrEstab` | The number of TCP connections for which the current state is either ESTABLISHED or CLOSE-WAIT.| |
| `snmp.tcpHCInSegs` | The total number of segments received, including those received in error. | |
| `snmp.tcpHCOutSegs` | The total number of segments sent, including those on current connections but excluding those containing only retransmitted octets. | |
| `snmp.tcpRetransSegs` | The total number of segments retransmitted; that is, the number of TCP segments transmitted containing one or more previously transmitted octets. |
| `snmp.tcpInErrs` | The total number of segments received in error (e.g., bad TCP checksums). | |
| `snmp.tcpOutRsts` | The number of TCP segments sent containing the RST flag.| |
| `snmp.udpHCInDatagrams` | The total number of UDP datagrams delivered to UDP users, for devices that can receive more than 1 million UDP datagrams per second. | |
| `snmp.udpNoPorts` | The total number of received UDP datagrams for which there was no application at the destination port. | |
| `snmp.udpInErrors` | The number of received UDP datagrams that could not be delivered for reasons other than the lack of an application at the destination port. | |
| `snmp.udpHCOutDatagrams` | The total number of UDP datagrams sent from this entity, for devices that can transmit more than 1 million UDP datagrams per second. ||

##### [F5 BIG-IP Profile][21]

MIBs needed for local reference: F5-BIGIP-SYSTEM-MIB, IF-MIB

| symbol | definition | tags |
| --- | --- | --- |
| `snmp.sysStatMemoryTotal`| The total memory available in bytes for TMM (Traffic Management Module). | |
| `snmp.sysStatMemoryUsed`| The memory in use in bytes for TMM (Traffic Management Module). | |
| `snmp.sysGlobalTmmStatMemoryTotal`| The total memory available in bytes for TMM (Traffic Management Module). | |
| `snmp.sysGlobalTmmStatMemoryUsed`| The memory in use in bytes for TMM (Traffic Management Module). | |
| `snmp.sysGlobalHostOtherMemoryTotal`| The total other non-TMM memory in bytes for the system. | |
| `snmp.sysGlobalHostOtherMemoryUsed`| The other non-TMM memory in bytes currently in use for the system. | |
| `snmp.sysGlobalHostSwapTotal`| The total swap in bytes for the system. | |
| `snmp.sysGlobalHostSwapUsed`| The swap in bytes currently in use for the system. | |
| `snmp.sysMultiHostCpuTable`| A table containing entries of system CPU usage information for a system. | |
| `snmp.sysMultiHostCpuUser`| The time spent by the specified processor in user context for the associated host. | `cpu`|
| `snmp.sysMultiHostCpuNice`| The time spent by the specified processor running niced processes for the associated host. |`cpu` |
| `snmp.sysMultiHostCpuSystem`| The time spent by the specified processor servicing system calls for the associated host. |`cpu` |
| `snmp.sysMultiHostCpuIdle`| The time spent by the specified processor doing nothing for the associated host. |`cpu` |
| `snmp.sysMultiHostCpuIrq`| The time spent by the specified processor servicing hardware interrupts for the associated host. | `cpu`|
| `snmp.sysMultiHostCpuSoftirq`| The time spent by the specified processor servicing soft interrupts for the associated host. | `cpu`|
| `snmp.sysMultiHostCpuIowait`| The time spent by the specified processor waiting for external I/O to complete for the associated host. |`cpu` |
| `snmp.sysTcpStatOpen`|The number of current open connections. | |
| `snmp.sysTcpStatCloseWait`| The number of current connections in CLOSE-WAIT/LAST-ACK. | |
| `snmp.sysTcpStatFinWait`| The number of current connections in FIN-WAIT/CLOSING. | |
|` snmp.sysTcpStatTimeWait`| The number of current connections in TIME-WAIT. | |
| `snmp.sysTcpStatAccepts`| The number of connections accepted. | |
| `snmp.sysTcpStatAcceptfails`| The number of connections not accepted. | |
| `snmp.sysTcpStatConnects`| The number of connections established. | |
| `snmp.sysTcpStatConnfails`| The number of connection failures. | |
| `snmp.sysUdpStatOpen`| The number of current open connections. | |
| `snmp.sysUdpStatAccepts`| The number of connections accepted. | |
| `snmp.sysUdpStatAcceptfails`| The number of connections not accepted. | |
| `snmp.sysUdpStatConnects`| The number of connections established. | |
| `snmp.sysUdpStatConnfails`| The number of connection failures. | |
| `snmp.sysClientsslStatCurConns`| The current number of concurrent connections with established SSL sessions being maintained by the filter. | |
| `snmp.sysClientsslStatEncryptedBytesIn`| The total encrypted bytes received. | |
| `snmp.sysClientsslStatEncryptedBytesOut`| The total encrypted bytes sent. | |
| `snmp.sysClientsslStatDecryptedBytesIn`| The total decrypted bytes received. | |
| `snmp.sysClientsslStatDecryptedBytesOut`| The total decrypted bytes sent. | |
| `snmp.sysClientsslStatHandshakeFailures`|The total number of handshake failures. | |
| `snmp.ifInErrors` | The number of inbound packets that contained errors preventing them from being deliverable to a higher-layer protocol. | `interface`|
| `snmp.ifOutErrors` | The number of outbound packets that could not be transmitted because of errors. | `interface` |
|` snmp.ifAdminStatus` | The desired state of the interface. | `interface`
| `snmp.ifOperStatus` | The current operational state of the interface. | `interface` |
| `snmp.tcpActiveOpens` | The number of times that TCP connections have made a direct transition to the SYN-SENT state from the CLOSED state. |  |
| `snmp.tcpPassiveOpens` | The number of times TCP connections have made a direct transition to the SYN-RCVD state from the LISTEN state. | |
| `snmp.tcpAttemptFails` | The number of times that TCP connections have made a direct transition to the CLOSED state from either the SYN-SENT state or the SYN-RCVD state, plus the number of times that TCP connections have made a direct transition to the LISTEN state from the SYN-RCVD state. | |
| `snmp.tcpEstabResets` | The number of times that TCP connections have made a direct transition to the CLOSED state from either the ESTABLISHED state or the CLOSE-WAIT state. | |
| `snmp.tcpCurrEstab` | The number of TCP connections for which the current state is either ESTABLISHED or CLOSE-WAIT.| |
| `snmp.tcpHCInSegs` | The total number of segments received, including those received in error. | |
| `snmp.tcpHCOutSegs` | The total number of segments sent, including those on current connections but excluding those containing only retransmitted octets. | |
| `snmp.tcpRetransSegs` | The total number of segments retransmitted; that is, the number of TCP segments transmitted containing one or more previously transmitted octets. |
| `snmp.tcpInErrs` | The total number of segments received in error (e.g., bad TCP checksums). | |
| `snmp.tcpOutRsts` | The number of TCP segments sent containing the RST flag.| |
| `snmp.udpHCInDatagrams` | The total number of UDP datagrams delivered to UDP users, for devices that can receive more than 1 million UDP datagrams per second. | |
| `snmp.udpNoPorts` | The total number of received UDP datagrams for which there was no application at the destination port. | |
| `snmp.udpInErrors` | The number of received UDP datagrams that could not be delivered for reasons other than the lack of an application at the destination port. | |
| `snmp.udpHCOutDatagrams` | The total number of UDP datagrams sent from this entity, for devices that can transmit more than 1 million UDP datagrams per second. ||


##### [Cisco c3850 Device Profile][22]

MIBs needed for local reference: CISCO-ENTITY-SENSOR-MIB, CISCO-ENTITY-FRU-CONTROL-MIB, CISCO-PROCESS-MIB, CISCO-IF-EXTENSION-MIB, IF-MIB, TCP-MIB, UDP-MIB

| symbol | definition | tags |
| --- | --- | --- |
| `snmp.entSensorValue` | The most recent measurement seen by the sensor. | `sensor_id`, `sensor_type`|
| `snmp.cefcFRUPowerAdminStatus` | Administratively desired FRU power state. | `fru` |  
| `snmp.cefcFRUPowerOperStatus` | Operational FRU power state. | `fru` |
| `snmp.cefcFRUCurrent` | Current supplied by the FRU (positive values) or current required to operate the FRU (negative values). | `fru` |    
| `snmp.cpmCPUTotalMonIntervalValue` | he overall CPU busy percentage in the last cpmCPUMonInterval period. | `cpu` |
| `snmp.cpmCPUMemoryUsed` | The overall CPU wide system memory which is currently under use. | `cpu` |
| `snmp.cpmCPUMemoryFree` | The overall CPU wide system memory which is currently free. | `cpu` |
| `snmp.cieIfLastInTime` | The elapsed time in milliseconds since last protocol input packet was received. | `interface`|
| `snmp.cieIfLastOutTime` | The elapsed time in milliseconds since last protocol  output packet was transmitted. | `interface`|
| `snmp.cieIfInputQueueDrops` | The number of input packets which were dropped.| `interface`|
| `snmp.cieIfOutputQueueDrops` | The  number of output packets dropped by the interface even though no error had been detected to prevent them being transmitted. | `interface`|
| `snmp.cieIfResetCount` | The number of times the interface was internally reset and brought up. | `interface` |
|` snmp.ifInErrors` | The number of inbound packets that contained errors preventing them from being deliverable to a higher-layer protocol. | `interface`|
| `snmp.ifOutErrors` | The number of outbound packets that could not be transmitted because of errors. | `interface` |
| `snmp.ifInDiscards` | The number of inbound packets which were chosen to be discarded even though no errors had been detected to prevent their being deliverable to a higher-layer protocol. | `interface` |
| `snmp.ifHCInOctets` | The total number of octets received on the interface, including framing characters. | `interface`|
| `snmp.ifHCOutOctets` | The total number of octets transmitted out of the interface, including framing characters.| `interface` |
| `snmp.ifOutDiscards` | The number of outbound packets which were chosen to be discarded even though no errors had been detected to prevent their being transmitted.|  `interface` |
| `snmp.ifAdminStatus` | The desired state of the interface. | `interface`|
| `snmp.ifOperStatus` | The current operational state of the interface. | `interface`
| `snmp.ifHCInOctets` | The total number of octets received on the interface, including framing characters. | `interface`|
| `snmp.ifHCInUcastPkts` | The number of packets, delivered by this sub-layer to a higher (sub-)layer, which were not addressed to a multicast or broadcast address at this sub-layer. | `interface`|
| `snmp.ifHCInBroadcastPkts` | The number of packets, delivered by this sub-layer to a higher (sub-)layer, which were addressed to a broadcast address at this sub-layer. | `interface`|
| `snmp.ifHCOutOctets` | The total number of octets transmitted out of the interface, including framing characters.| `interface` |
| `snmp.ifHCOutUcastPkts` | The total number of packets that higher-level protocols requested be transmitted, and which were not addressed to a multicast or broadcast address at this sub-layer, including those that were discarded or not sent.| `interface` |
| `snmp.ifHCOutMulticastPkts` | The total number of packets that higher-level protocols requested be transmitted, and which were addressed to a multicast address at this sub-layer, including those that were discarded or not sent. | `interface` |
| `snmp.ifHCOutBroadcastPkts` | The total number of packets that higher-level protocols requested be transmitted, and which were addressed to a broadcast address at this sub-layer, including those that were discarded or not sent.| `interface` |



#### Containerized
For containerized environments, see the [Autodiscovery Integration Templates][16] for guidance on applying the parameters below.


### Validation

[Run the Agent's status subcommand][12] and look for `snmp` under the Checks section.

## Data Collected
### Metrics

The SNMP check submits specified metrics under the `snmp.*` namespace.

### Events

The SNMP check does not include any events.

### Service Checks

**snmp.can_check**:<br>
Returns `CRITICAL` if the Agent cannot collect SNMP metrics, otherwise returns `OK`.

## Troubleshooting

Need help? Contact [Datadog support][13].

## Further Reading

Additional helpful documentation, links, and articles:

* [Does Datadog have a list of commonly used/compatible OIDs with SNMP?][14]
* [Monitoring Unifi devices using SNMP and Datadog][15]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/conf.yaml.example
[4]: http://snmplabs.com/pysnmp/docs/api-reference.html#user-based
[5]: http://snmplabs.com/pysnmp/index.html
[6]: https://stackoverflow.com/questions/35204995/build-pysnmp-mib-convert-cisco-mib-files-to-a-python-fails-on-ubuntu-14-04
[7]: https://github.com/DataDog/dd-agent/blob/master/CHANGELOG.md#dependency-changes-3
[8]: https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/conf.yaml.example#L3
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[10]: https://docs.datadoghq.com/developers/metrics/custom_metrics
[11]: https://docs.datadoghq.com/account_management/billing/custom_metrics
[12]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[13]: https://docs.datadoghq.com/help
[14]: https://docs.datadoghq.com/integrations/faq/for-snmp-does-datadog-have-a-list-of-commonly-used-compatible-oids
[15]: https://medium.com/server-guides/monitoring-unifi-devices-using-snmp-and-datadog-c8093a7d54ca
[16]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[17]: https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/conf.yaml.example
[18]: https://github.com/DataDog/integrations-core/tree/master/snmp/datadog_checks/snmp/data/profiles
[19]: https://docs.datadoghq.com/tagging/
[20]: https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/profiles/generic-router.yaml
[21]: https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/profiles/f5-big-ip.yaml
[22]: https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/profiles/cisco-3850.yaml
