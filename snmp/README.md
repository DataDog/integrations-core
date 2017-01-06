# Snmp Integration

## Overview

Use the SNMP Agent Check to:

* Monitor all your network devices
* Correlate their performance with the rest of your applications

## Installation

Install the `dd-check-snmp` package manually or with your favorite configuration manager

## Configuration

1. Configure the Agent to connect to your network devices, edit conf.yaml
```
init_config:
   - mibs_folder: /path/to/your/additional/mibs

instances:
   -   ip_address: localhost
       port: 161
       community_string: public
       tags:
            - optional_tag1
            - optional_tag2
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

You can find more information on the configuration on the [documentation website](http://docs.datadoghq.com/integrations/snmp/)

2. Restart the Agent

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        snmp
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The snmp check is compatible with all major platforms
