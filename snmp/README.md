# SNMP Check

## Overview

This check lets you collect SNMP metrics from your network devices.

## Setup
### Installation

The SNMP check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on any host where you want to run the check.

### Configuration

The SNMP check doesn't collect anything by default; you have to tell it specifically what to collect.

Here's an example `snmp.yaml`. See the [sample snmp.yaml](https://github.com/DataDog/integrations-core/blob/master/snmp/conf.yaml.example) for all available configuration options:

```
init_config:
   - mibs_folder: /path/to/your/additional/mibs

instances:
   - ip_address: localhost
     port: 161
     community_string: public
#    snmp_version: 1 # set to 1 if your devices use SNMP v1; no need to set otherwise, the default is 2
     timeout: 1      # in seconds; default is 1
     retries: 5
#    enforce_mib_constraints: false # set to false to NOT verify that returned values meet MIB constraints; default is true
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

    metrics:
      - MIB: IP-MIB
        table: ipSystemStatsTable
        symbols:
          - ipSystemStatsInReceives
        metric_tags:
          - tag: ipversion
        index: 1

You can also gather tags based on the indices of your row, in case they are meaningful. In the above example, the first row index contains the ip version that the row describes (ipv4 vs. ipv6)

#### Use your own MIB

To use your own MIB with the datadog-agent, you need to convert them to the pysnmp format. This can be done using the ```build-pysnmp-mibs``` script that ships with pysnmp.

It has a dependency on ```smidump```, from the libsmi2ldbl package so make sure it is installed. Make also sure that you have all the dependencies of your MIB in your mib folder or it won't be able to convert your MIB correctly.

##### Run

    $ build-pysnmp-mib -o YOUR-MIB.py YOUR-MIB.mib

where YOUR-MIB.mib is the MIB you want to convert.

Put all your pysnmp mibs into a folder and specify this folder's path in ```snmp.yaml``` file, in the ```init_config``` section.


---

[Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent) to start sending SNMP metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `snmp` under the Checks section:

```
  Checks
  ======
    [...]

    snmp
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The snmp check is compatible with all major platforms.

## Data Collected
### Metrics

The SNMP check will submits specified metrics under the `snmp.*` namespace.

### Events
The SNMP check does not include any event at this time.

### Service Checks

**snmp.can_check**:

Returns CRITICAL if the Agent cannot collect SNMP metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
### Datadog Blog
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)

### Knowledge Base

* [For SNMP, does Datadog have a list of commonly used/compatible OIDs?  ](https://docs.datadoghq.com/integrations/faq/for-snmp-does-datadog-have-a-list-of-commonly-used-compatible-oids)
