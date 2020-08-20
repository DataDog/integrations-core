# SNMP Check

## Overview

Simple Network Management Protocol (SNMP) is a standard for monitoring network-connected devices, such as routers, switches, servers, and firewalls. This check collects SNMP metrics from your network devices.

SNMP uses sysObjectIDs (System Object Identifiers) to uniquely identify devices, and OIDs (Object Identifiers) to uniquely identify managed objects. OIDs follow a hierarchical tree pattern: under the root is ISO, which is numbered 1. The next level is ORG and numbered 3 and so on, with each level being separated by a `.`.

A MIB (Management Information Base) acts as a translator between OIDs and human readable names, and organizes a subset of the hierarchy. Because of the way the tree is structured, most SNMP values start with the same set of objects:

* `1.3.6.1.1`: (MIB-II) A standard that holds system information like uptime, interfaces, and network stack.
* `1.3.6.1.4.1`: A standard that holds vendor specific information.

## Setup

### Installation

The SNMP check is included in the [Datadog Agent][1] package. No additional installation is necessary.

### Configuration

Edit the configuration options in the `snmp.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample snmp.d/conf.yaml][3] for all available configuration options.

The Datadog SNMP check supports collecting metrics from individual devices, or auto-discovering devices (unique IP addresses) on entire subnets.

Which collection strategy to choose mainly depends on how many devices are present on your network, and how dynamic the network is (i.e. how frequently devices are added or removed):

- For small and mostly static networks, see [Monitoring individual devices](#monitoring-individual-devices).
- For larger and/or dynamic networks, see [Autodiscovery](#autodiscovery).

Regardless of the collection strategy, you can leverage Datadog's [`sysObjectID` mapped device profiles](#sysobjectid-mapped-device-profiles) to automatically collect relevant metrics from your devices.

#### Monitoring individual devices

The easiest way to get started with the SNMP integration is to point it at the IP address of an SNMP device.

For SNMPv2 devices:

1. Configure an instance specifying i) the IP address of the device, ii) the _community string_ of the device:

    ```yaml
    instances:
      - ip_address: "<IP_ADDRESS>"
        community_string: "<COMMUNITY_STRING>"
    ```

2. [Restart the Agent][31].

For SNMPv3 devices:

1. Configure an instance specifying i) the IP address of the device, ii) SNMPv3 credentials of the device, i.e. `user` and any of `auth_protocol`, `auth_key`, `priv_protocol`, and `priv_key` (as appropriate for your device):

    ```yaml
    instances:
      - ip_address: "<IP_ADDRESS>"
        user: "<USER>"
        ## Configure these as appropriate
        # authProtocol: SHA
        # authKey: "<AUTH_KEY>"
        # privProtocol: AES
        # privKey: "<PRIV_KEY>"
    ```

2. [Restart the Agent][31].

The Agent will then start collecting relevant metrics by matching your device against one of [Datadog's out-of-the-box device profiles](#metric-definition-by-profile).

Once metrics are reporting, you can expand your setup in various ways:

* Add more instances to collect metrics from more devices on your network.
* Consider using [Autodiscovery](#autodiscovery) if you need to collect metrics from lots of devices across a dynamic network.

#### Autodiscovery

As an alternative to specifying individual devices, you can use autodiscovery to automatically discover all the devices on your network.

Autodiscovery will poll each IP on the configured subnet, and check for a response from the SNMP device. The Datadog Agent will then lookup the `sysObjectID` of the discovered device, and map it to one of [Datadog's out-of-the-box device profiles](#metric-definition-by-profile), which consist of lists of predefined metrics to be collected for various types of devices.

To use Autodiscovery with the SNMP check:

1. Install or upgrade the Datadog Agent to v6.16+. For platform specific instructions, see the [Datadog Agent][4] documentation.

2. Configure the SNMP check with [snmp.d/conf.yaml][3]. The following parameters are available. See the [sample config](#sample-config) for required parameters, default values, and examples.

| Parameter                    | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
|------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `profiles`                   | A list of profiles to use. A profile is a collection of OIDs the Datadog Agent collects metrics and associated tags from and a complete list of Datadog supported profiles can be found in [Github][5]. By default, all profiles shipped by the agent and in the configuration directory are loaded.  To customize the specific profiles for collection, they can be explicitly referenced by filename under `definition_file`, or written inline under `definition`. Any of the OOTB Datadog profiles can be listed by their name. Additional custom profiles can be referenced by the file path in the config, or simply dropped in the configuration directory. **Note**: The generic profile is `generic_router.yaml`, which should work for routers, switches, etc. |
| `network_address`            | The subnet and mask written in IPv4 notation for the Agent to scan and discover devices on.                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `community_string`           | For use with SNMPv1 and SNMPv2                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `snmp_version`               | The SNMP version you are using.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `port`                       | The port for the Datadog Agent to listen on.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `timeout`                    | The number of seconds before timing out.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `retries`                    | The number of retries before failure.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `discovery_interval`         | The interval between discovery scans.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `discovery_allowed_failures` | The number of times a discovered host can fail before being removed from the list of discovered devices.                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `bulk_threshold`             | The number of symbols in a table that triggers a BULK request. This parameter is only relevant for SNMPv > 1.                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `tags`                       | A list of global tags to add to all SNMP metrics. Read more about [tagging in Datadog][6].                                                                                                                                                                                                                                                                                                                                                                                                                                                 |

##### Sample config

```yaml
init_config:

instances:
  -
    ## @param network_address - string - optional
    network_address: "<NETWORK_ADDRESS>"

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
       - "<KEY_1>:<VALUE_1>"
       - "<KEY_2>:<VALUE_2>"
```

##### sysObjectID mapped device profiles

Profiles allow the SNMP check to reuse metric definitions across several device types or instances. Profiles define metrics the same way as instances, either inline in the configuration file or in separate files. Each instance can only match a single profile. For example, you can define a profile in the `init_config` section:

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

```yaml
instances:
   - ip_address: 192.168.34.10
     profile: my-profile
   - ip_address: 192.168.34.11
     # Don't need anything else here, the check will query the sysObjectID
     # and use the profile if it matches.
```

If necessary, additional metrics can be defined in the instances. These metrics are collected in addition to those in the profile.

#### Metric definition by profile

Profiles can be used interchangeably, such that devices that share MIB dependencies can reuse the same profiles. For example, the Cisco c3850 profile can be used across many Cisco switches.

* [Generic router][7] _(Default profile in case no other profile matches)_
* [Cisco ASA 5525][8]
* [Cisco c3850][9]
* [Cisco Nexus][10]
* [Cisco Meraki][11]
* [Cisco UC Virtual Machine][26]
* [Cisco ICM][27]
* [Cisco ISR 4431][28]
* [Dell iDRAC][12]
* [Dell Poweredge][13]
* [F5 Big IP][14]
* [Fortinet FortiGate][29]
* [HP iLO4][15]
* [HPE Proliant][16]
* [NetApp][30]
* [Palo Alto][17]
* [Checkpoint Firewall][18]
* [Isilon][24]
* [APC UPS][25]

### Validation

[Run the Agent's status subcommand][19] and look for `snmp` under the Checks section.

## Data Collected

The SNMP check submits specified metrics under the `snmp.*` namespace. **Metrics collected depends on the integration being configured with the corresponding profile**.

### Metrics

See [metadata.csv][20] for a list of metrics provided by this check.

### Events

The SNMP check does not include any events.

### Service Checks

**snmp.can_check**:<br>
Returns `CRITICAL` if the Agent cannot collect SNMP metrics, otherwise returns `OK`.

## Troubleshooting

Need help? Contact [Datadog support][21].

## Further Reading

Additional helpful documentation, links, and articles:

* [Does Datadog have a list of commonly used/compatible OIDs with SNMP?][22]
* [Monitoring Unifi devices using SNMP and Datadog][23]

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/
[5]: https://github.com/DataDog/integrations-core/tree/master/snmp/datadog_checks/snmp/data/profiles
[6]: https://docs.datadoghq.com/tagging/
[7]: https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/profiles/generic-router.yaml
[8]: https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/profiles/cisco-asa-5525.yaml
[9]: https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/profiles/cisco-3850.yaml
[10]: https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/profiles/cisco-nexus.yaml
[11]: https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/profiles/meraki-cloud-controller.yaml
[12]: https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/profiles/idrac.yaml
[13]: https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/profiles/dell-poweredge.yaml
[14]: https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/profiles/f5-big-ip.yaml
[15]: https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/profiles/hp-ilo4.yaml
[16]: https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/profiles/hpe-proliant.yaml
[17]: https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/profiles/palo-alto.yaml
[18]: https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/profiles/checkpoint-firewall.yaml
[19]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[20]: https://github.com/DataDog/integrations-core/blob/master/snmp/metadata.csv
[21]: https://docs.datadoghq.com/help/
[22]: https://docs.datadoghq.com/integrations/faq/for-snmp-does-datadog-have-a-list-of-commonly-used-compatible-oids/
[23]: https://medium.com/server-guides/monitoring-unifi-devices-using-snmp-and-datadog-c8093a7d54ca
[24]: https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/profiles/isilon.yaml
[25]: https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/profiles/apc-ups.yaml
[26]: https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/profiles/cisco_uc_virtual_machine.yaml
[27]: https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/profiles/cisco_icm.yaml
[28]: https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/profiles/cisco_isr_4431.yaml
[29]: https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/profiles/fortinet-fortigate.yaml
[30]: https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/profiles/netapp.yaml
[31]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
