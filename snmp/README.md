# SNMP Check

## Overview

This check lets you collect SNMP metrics from your network devices.

## Setup
### Installation

The SNMP check is included in the [Datadog Agent][1] package, so you don't need to install anything else on any host where you want to run the check.

### Configuration

The SNMP check doesn't collect anything by default; you have to tell it specifically what to collect.

Here's an example of `snmp.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][11]. See the [sample snmp.d/conf.yaml][2] for all available configuration options:

```
init_config:
   - mibs_folder: /path/to/your/additional/mibs

instances:
   - ip_address: localhost
     port: 161
     community_string: public
  #  snmp_version: 1 # set to 1 if your devices use SNMP v1; no need to set otherwise, the default is 2
     timeout: 1      # in seconds; default is 1
     retries: 5
  #  enforce_mib_constraints: false # set to false to NOT verify that returned values meet MIB constraints; default is true
     metrics:
       - MIB: UDP-MIB
         symbol: udpInDatagrams
       - OID: 1.3.6.1.2.1.6.5
         name: tcpPassiveOpens
       - MIB: IF-MIB
         table: ifTable
         symbols:
           - ifInOctets
           - ifOutOctets
         metric_tags:
           - tag: interface
             column: ifDescr
```

List each SNMP device as a distinct instance, and for each instance, list any SNMP counters and gauges you like in the `metrics` option. There are a few ways to specify what metrics to collect.

#### MIB and symbol

```
metrics:
  - MIB: UDP-MIB
    symbol: udpInDatagrams
```

#### OID and name

```
metrics:
   - OID: 1.3.6.1.2.1.6.5
     name: tcpActiveOpens # what to use in the metric name; can be anything
```

#### MIB and table

```
metrics:
  - MIB: IF-MIB
    table: ifTable
    symbols:
       - ifInOctets      # row whose value becomes metric value
    metric_tags:
       - tag: interface  # tag name
         column: ifDescr # the column name to get the tag value from, OR
         #index: 1       # the column index to get the tag value from
```

This lets you collect metrics on all rows in a table (`symbols`) and specify how to tag each metric (`metric_tags`).

In the above example, the agent would gather the rate of octets received on each interface and tag it with the interface name (found in the ifDescr column), resulting in a tag such as ```interface:eth0```

```
metrics:
  - MIB: IP-MIB
    table: ipSystemStatsTable
    symbols:
      - ipSystemStatsInReceives
    metric_tags:
      - tag: ipversion
    index: 1
```

You can also gather tags based on the indices of your row, in case they are meaningful. In the above example, the first row index contains the ip version that the row describes (ipv4 vs. ipv6)

#### Use your own MIB

To use your own MIB with the datadog-agent, convert them to the pysnmp format. This can be done using the ```build-pysnmp-mibs``` script that ships with pysnmp, but the `build-pysnmp-mib` script has been made obsolete since pysnmp 4.3 (Reference [here][9]); `mibdump.py` replaces it.

Since Datadog agent version 5.14, our PySNMP dependency has been upgraded from version 4.25 to 4.3.5 (Reference on our [changelog][8]). Meaning the `build-pysnmp-mib` which shipped with our agent from version 5.13.x and earlier has also been replaced with `mibdump.py`.
 
Finding the location of mibdump.py

```
find /opt/datadog-agent/ -type f -name build-pysnmp-mib.py -o -name mibdump.py
/opt/datadog-agent/bin/mibdump.py
```

Below is the format to use the script:

```
/opt/datadog-agent/bin/mibdump.py --mib-source /path/to/mib/files/  --mib-source http://mibs.snmplabs.com/asn1/@mib@ --destination-directory=/path/to/converted/mib/pyfiles/ --destination-format=pysnmp <MIB_FILE_NAME>
```

Example using the `CISCO-TCP-MIB.my`:

```
 # /opt/datadog-agent/bin/mibdump.py --mib-source /path/to/mib/files/  --mib-source http://mibs.snmplabs.com/asn1/@mib@ --destination-directory=/opt/datadog-agent/pysnmp/custom_mibpy/ --destination-format=pysnmp CISCO-TCP-MIB

 Source MIB repositories: /path/to/mib/files/, http://mibs.snmplabs.com/asn1/@mib@
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


 #ls /opt/datadog-agent/pysnmp/custom_mibpy/
CISCO-SMI.py CISCO-SMI.pyc CISCO-TCP-MIB.py CISCO-TCP-MIB.pyc

```

The Agent with the path looks for the converted MIB Python files by specifying the destination path with mibs_folder: in the [SNMP yaml configuration][10].

---

[Restart the Agent][3] to start sending SNMP metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][4] and look for `snmp` under the Checks section.

## Data Collected
### Metrics

The SNMP check will submits specified metrics under the `snmp.*` namespace.

### Events
The SNMP check does not include any events at this time.

### Service Checks

**snmp.can_check**:

Returns CRITICAL if the Agent cannot collect SNMP metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support][5].

## Further Reading

* [For SNMP, does Datadog have a list of commonly used/compatible OIDs?  ][7]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://docs.datadoghq.com/help/
[7]: https://docs.datadoghq.com/integrations/faq/for-snmp-does-datadog-have-a-list-of-commonly-used-compatible-oids
[8]: https://github.com/DataDog/dd-agent/blob/master/CHANGELOG.md#dependency-changes-3
[9]: https://stackoverflow.com/questions/35204995/build-pysnmp-mib-convert-cisco-mib-files-to-a-python-fails-on-ubuntu-14-04
[10]: https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/conf.yaml.example#L3
[11]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
