# SNMP Check

## Overview

Simple Network Management Protocol (SNMP) is a standard for monitoring network-connected devices, such as routers, switches, servers, and firewalls. This check collects SNMP metrics from your network devices.

SNMP uses OIDs (Object Identifiers) to uniquely identify managed objects. OIDs follow a hierarchical tree pattern: under the root is ISO which is numbered 1, then next level is ORG and numbered 3 and so on, with each level being separated by a `..`

A MIB (Management Information Base) acts as a translator between OIDs and human readable names, and organizes a subset of the hierarchy. Because of the way the tree is structured, most SNMP values start with the same set of objects: 1.3.6.1.1 for MIB-2 which is a standard that holds system information like uptime, interfaces, network stack, and 1.3.6.1.4.1 which holds vendor specific information.

## Setup
### Installation

The SNMP check is included in the [Datadog Agent][1] package. No additional installation is necessary.

### Configuration
#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

The SNMP check doesn't collect anything by default. Specify metrics to collect by updating your `snmp.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample snmp.d/conf.yaml][3] for all available configuration options.

##### SNMP v1-v2 configuration

```yaml
init_config:
  ## @param mibs_folder - string - required
  # mibs_folder: <PATH_TO_ADDITIONAL_MIBS>

  ## @param global_metrics - list of elements - (required if none at the instance level)
  # global_metrics:
  ## - MIB: <MIB_NAME>
  ##   symbol: <SYMBOL>

instances:
    ## @param ip_address - string - required
  - ip_address: localhost

    ## @param port - integer - required
    ## Default SNMP port.
    #
    port: 161

    ## @param community_string - string - optional
    # community_string: public

    ## @param snmp_version - integer - optional - default: 2
    # snmp_version: 2

    ## @param metrics - list of elements - (required if none at the init_config level)
    metrics:
    - MIB: <MIB_NAME>
      symbol: <SYMBOL>
    - OID: <OID>
      name: <OID_NAME>
      metric_tags:
        - <TAG>
```

##### SNMP v3 configuration

**Note**: See the [SNMP Library reference][4] for all configuration options.

```yaml
init_config:
  ## @param mibs_folder - string - required
  # mibs_folder: <PATH_TO_ADDITIONAL_MIBS>

  ## @param global_metrics - list of elements - (required if none at the instance level)
  # global_metrics:
  ## - MIB: <MIB_NAME>
  ##   symbol: <SYMBOL>

instances:
    ## @param ip_address - string - required
  - ip_address: localhost

    ## @param port - integer - required
    port: 161

    ## @param snmp_version - integer - optional - default: 2
    snmp_version: 3

    ## @param user - string - required
    user: <USERNAME>

    ## @param authProtocol - string - required
    authProtocol: <AUTHENTICATION_PROTOCOL>

    ## @param authKey - string - required
    authKey: <AUTHENTICATION_TYPE_KEY>

    ## @param privProtocol - string - required
    privProtocol: <PRIVACY_TYPE>

    ## @param privKey - string - required
    privKey: <PRIVACY_TYPE_KEY>

    ## @param metrics - list of elements - (required if none at the init_config level)
    metrics:
    - MIB: <MIB_NAME>
      symbol: <SYMBOL>
    - OID: <OID>
      name: <OID_NAME>
      metric_tags:
        - <TAG>
```

* List each SNMP device as a distinct instance.
* For each instance, list your choice of SNMP counters and gauges in under `metrics`.

There are a few ways to specify the metrics to collect. See the [sample snmp.d/conf.yaml][3] for examples.

* MIB and symbol
* OID and name
* MIB and table

##### Use your own MIB

To use your own MIB with the Datadog Agent, convert it to the [PySNMP][5] format. This can be done using the `mibdump.py` script that ships with PySNMP. `mibdump.py` replaces `build-pysnmp-mib` which was made obsolete in [PySNMP 4.3+][6].

Since Datadog Agent v5.14, the Agent's PySNMP dependency has been upgraded from version 4.25 to 4.3.5 (refer to the [changelog][7]). This means that the `build-pysnmp-mib` which shipped with the Agent from version 5.13.x and earlier has also been replaced with `mibdump.py`.

In Linux, find the location of `mibdump.py`, run:

```shell
$ find /opt/datadog-agent/ -type f -name build-pysnmp-mib.py -o -name mibdump.py
/opt/datadog-agent/embedded/bin/mibdump.py
```

Windows example:

```powershell
C:\>dir mibdump.py /s

Directory of C:\Program Files\Datadog\Datadog Agent\embedded\Scripts
```

In Linux, use this format for the script:

```shell
<PATH_TO_FILE>/mibdump.py \
  --mib-source <PATH_TO_MIB_FILES> \
  --mib-source http://mibs.snmplabs.com/asn1/@mib@ \
  --destination-directory=<PATH_TO_CONVERTED_MIB_PYFILES> \
  --destination-format=pysnmp <MIB_FILE_NAME>
```

Windows Powershell example:

Agent versions <=6.11:

```powershell
PS> & 'C:\Program Files\Datadog\Datadog Agent\embedded\python.exe' '<PATH_TO_FILE>\mibdump.py' `
  --mib-source <PATH_TO_MIB_SOURCE> `
  --mib-source http://mibs.snmplabs.com/asn1/@mib@ `
  --destination-directory=<PATH_TO_MIB_DESTINATION> `
  --destination-format=pysnmp <MIB_FILE_NAME>
```

Agent versions >=6.12:

```powershell
PS> & 'C:\Program Files\Datadog\Datadog Agent\embedded<PYTHON_MAJOR_VERSION>\python.exe' '<PATH_TO_FILE>\mibdump.py' `
  --mib-source <PATH_TO_MIB_SOURCE> `
  --mib-source http://mibs.snmplabs.com/asn1/@mib@ `
  --destination-directory=<PATH_TO_MIB_DESTINATION> `
  --destination-format=pysnmp <MIB_FILE_NAME>
```

Example using the `CISCO-TCP-MIB.my`:

```
 # /opt/datadog-agent/embedded/bin/mibdump.py --mib-source <PATH_TO_MIB_FILE>  --mib-source http://mibs.snmplabs.com/asn1/@mib@ --destination-directory=/opt/datadog-agent/pysnmp/custom_mibpy/ --destination-format=pysnmp CISCO-TCP-MIB

 Source MIB repositories: <PATH_TO_MIB_FILE>, http://mibs.snmplabs.com/asn1/@mib@
 Borrow missing/failed MIBs from: http://mibs.snmplabs.com/pysnmp/notexts/@mib@
 Existing/compiled MIB locations: pysnmp.smi.mibs, pysnmp_mibs
 Compiled MIBs destination directory: /opt/datadog-agent/pysnmp/custom_mibpy/
 MIBs excluded from code generation: INET-ADDRESS-MIB, PYSNMP-USM-MIB, RFC-1212, RFC-1215, RFC1065-SMI, RFC1155-SMI, RFC1158-MIB, RFC1213-MIB, SNMP-FRAMEWORK-MIB, SNMP-TARGET-MIB, SNMPv2-CONF, SNMPv2-SMI, SNMPv2-TC, SNMPv2-TM, TRANSPORT-ADDRESS-MIB
 MIBs to compile: CISCO-TCP
 Destination format: pysnmp
 Parser grammar cache directory: not used
 Also compile all relevant MIBs: yes
 Rebuild MIBs regardless of age: no
 Dry run mode: no Create/update MIBs: yes
 Byte-compile Python modules: yes (optimization level no)
 Ignore compilation errors: no
 Generate OID->MIB index: no
 Generate texts in MIBs: no
 Keep original texts layout: no
 Try various file names while searching for MIB module: yes
 Created/updated MIBs: CISCO-SMI, CISCO-TCP-MIB (CISCO-TCP)
 Pre-compiled MIBs borrowed:
 Up to date MIBs: INET-ADDRESS-MIB, SNMPv2-CONF, SNMPv2-SMI, SNMPv2-TC, TCP-MIB
 Missing source MIBs:
 Ignored MIBs:
 Failed MIBs:

 # ls /opt/datadog-agent/pysnmp/custom_mibpy/
CISCO-SMI.py CISCO-SMI.pyc CISCO-TCP-MIB.py CISCO-TCP-MIB.pyc

```

The Agent looks for the converted MIB Python files by specifying the destination path with `mibs_folder` in the [SNMP YAML configuration][8].

[Restart the Agent][9] to start sending SNMP metrics to Datadog.

##### Profiles

To group configurations, the check allows defining profiles to reuse metric definitions on several instances. Profiles define metrics the same way as instances, either inline in the configuration file or in separate files. Each instance can only match a single profile. For example, you can define a profile in the `init_config` section:

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

If necessary, additional metrics can be defined in the instances. These metrics are collected alongside those in the profile.

#### Containerized
For containerized environments, see the [Autodiscovery Integration Templates][16] for guidance on applying the parameters below.

##### SNMP v1

| Parameter              | Value                                                                                                                                                                                              |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------                                                        |
| `<INTEGRATION_NAME>`   | `snmp`                                                                                                                                                                                             |
| `<INIT_CONFIG>`        | `{"mibs_folder":"<PATH_TO_ADDITIONAL_MIBS>"}`                                                                                                                                                      |
| `<INSTANCE_CONFIG>`    | ```{"ip_address":"%%host%%", "port":"161", "community_string":"<COMMUNITY_NAME>", "snmp_version":"1", "metrics":[{"MIB":"<MIB_NAME>","symbol":"<SYMBOL>"},{"OID":"<OID>","name":"<OID_NAME>"}]}``` |

##### SNMP v2

| Parameter              | Value                                                                                                                                                                          |
| ---------------------- | ------------------------------------------------------------------------------------------------                                                                               |
| `<INTEGRATION_NAME>`   | `snmp`                                                                                                                                                                         |
| `<INIT_CONFIG>`        | `{"mibs_folder":"<PATH_TO_ADDITIONAL_MIBS>"}`                                                                                                                                  |
| `<INSTANCE_CONFIG>`    | ```{"ip_address":"%%host%%", "port":"161", "community_string":"<COMMUNITY_NAME>", "metrics":[{"MIB":"<MIB_NAME>","symbol":"<SYMBOL>"},{"OID":"<OID>","name":"<OID_NAME>"}]}``` |

##### SNMP v3

**Note**: See the [SNMP Library reference][4] for all configuration options.

| Parameter              | Value                                                                                                                                                                                                                                                                                                                  |
| ---------------------- | -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------      |
| `<INTEGRATION_NAME>`   | `snmp`                                                                                                                                                                                                                                                                                                                 |
| `<INIT_CONFIG>`        | `{"mibs_folder":"<PATH_TO_ADDITIONAL_MIBS>"}`                                                                                                                                                                                                                                                                          |
| `<INSTANCE_CONFIG>`    | ```{"ip_address":"%%host%%", "port":"161", "snmp_version":"3", "user":"<USER_NAME>", "authKey":"<PASSWORD>", "privKey":"<PRIVACY_TYPE_KEY>", "authProtocol":"<AUTHENTICATION_PROTOCOL>", "privProtocol":"<PRIVACY_TYPE>", "metrics":[{"MIB":"<MIB_NAME>","symbol":"<SYMBOL>"},{"OID":"<OID>","name":"<OID_NAME>"}]}``` |


### Custom metrics
Metrics collected by the SNMP integration are considered [custom metrics][10], which impacts your [bill][11].

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

* [For SNMP, does Datadog have a list of commonly used/compatible OIDs?][14]
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
