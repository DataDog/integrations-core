# Profile format reference

## Overview

SNMP profiles are our way of providing out-of-the-box monitoring for certain makes and models of network devices.

An SNMP profile is materialised as a YAML file with the following structure:

```yaml
sysobjectid: <x.y.z...>

# extends:
#   <Optional list of base profiles to extend from...>

metrics:
  # <List of metrics to collect...>

# metric_tags:
#   <Optional list of tags to apply to collected metrics>
```

## Fields

### `sysobjectid`

_(Required)_

The `sysobjectid` field is used to match profiles against devices during device autodiscovery.

It can refer to a fully-defined OID for a specific device make and model:

```yaml
sysobjectid: 1.3.6.1.4.1.232.9.4.10
```

or a wildcard pattern to address multiple device models:

```yaml
sysobjectid: 1.3.6.1.131.12.4.*
```

### `extends`

_(Optional)_

This field can be used to include metrics and metric tags from other so-called _base profiles_. Base profiles can derive from other base profiles to build a hierarchy of reusable profile mixins.

!!! important
    All device profiles should extend from the `_base.yaml` profile, which defines items that should be collected for all devices.

Example:

```yaml
extends:
  - _base.yaml
  - _generic-router-if.yaml  # Include basic metrics from IF-MIB.
```

### `metrics`

_(Required)_

Entries in the `metrics` field define which metrics will be collected by the profile. They can reference either a single OID (a.k.a _symbol_), or an SNMP table.

#### Symbol metrics

In profiles, OIDs can be specified as entries containing the `symbol` field:

```yaml
metrics:
  - MIB: TCP-MIB
    symbol:
      OID: 1.3.6.1.2.1.6.5
      name: tcpActiveOpens
```

#### Table metrics

An SNMP table is an object that is composed of multiple entries.

In a MIB file, tables be recognized by the following syntax:

```asn
exampleTable OBJECT-TYPE
    SYNTAX   SEQUENCE OF exampleEntry
    -- ...

exampleEntry OBJECT-TYPE
   -- ...
   ::= { exampleTable 1 }
```

In profiles, tables can be specified as entries containing the `table` and `symbols` fields:

```yaml
metrics:
  - MIB: CISCO-PROCESS-MIB
    table:
      # Identification of the table which metrics come from.
      # For example, this device has multiple CPU units; each row
      # in this table contains information about a single CPU unit.
      OID: 1.3.6.1.4.1.9.9.109.1.1.1
      name: cpmCPUTotalTable
    symbols:
      # List of symbols ('columns') to retrieve.
      # Same format as for a single OID.
      # Each row in the table will emit these metrics.
      # For example, if we have N CPU units, then the
      # integration will emit N `snmp.cpmCPUMemoryUsed` metrics.
      - OID: 1.3.6.1.4.1.9.9.109.1.1.1.1.12
        name: cpmCPUMemoryUsed
      # ...
```

#### Table metrics tagging

It is possible to add tags to metrics retrieved from a table in three ways:

- Using an index:

```yaml
metrics:
  - MIB: CISCO-PROCESS-MIB
    table:
      OID: 1.3.6.1.4.1.9.9.109.1.1.1
      name: cpmCPUTotalTable
    symbols:
      - OID: 1.3.6.1.4.1.9.9.109.1.1.1.1.12
        name: cpmCPUMemoryUsed
    metric_tags:
      # Add a 'cpu:<row_index>' tag to each metric of each row,
      # whose value is the index of the row in the table.
      # This allows querying metrics for a given CPU unit, e.g. 'cpu:1'.
      - tag: cpu
        index: 1
```

- Using a column within the same table:

```yaml
metrics:
  - MIB: IF-MIB
    table:
      OID: 1.3.6.1.2.1.2.2
      name: ifTable
    symbols:
      - OID: 1.3.6.1.2.1.2.2.1.14
        name: ifInErrors
      # ...
    metric_tags:
      # Add an 'interface' tag to each metric of each row,
      # whose value is obtained from the 'ifDescr' column of the row.
      # This allows querying metrics by interface, e.g. 'interface:eth0'.
      - tag: interface
        column:
          OID: 1.3.6.1.2.1.2.2.1.2
          name: ifDescr
```

- Using a column from a different table.

```yaml
metrics:
  - MIB: CISCO-IF-EXTENSION-MIB
    forced_type: monotonic_count
    table:
      OID: 1.3.6.1.4.1.9.9.276.1.1.2
      name: cieIfInterfaceTable
    symbols:
      - OID: 1.3.6.1.4.1.9.9.276.1.1.2.1.1
        name: cieIfResetCount
    metric_tags:
      - MIB: IF-MIB
        column:
          OID: 1.3.6.1.2.1.31.1.1.1.1
          name: ifName
        table: ifXTable
        tag: interface
```

### `metric_tags`

_(Optional)_

This field is used to apply tags to all metrics collected by the profile. It has the same meaning than the instance-level config option (see [`conf.yaml.example`](https://github.com/DataDog/integrations-core/blob/master/snmp/datadog_checks/snmp/data/conf.yaml.example)). Several collection methods are supported.

```yaml
metric_tags:
  - # From a symbol
    MIB: SNMPv2-MIB
    symbol: sysName
    tag: snmp_host
  - # From an OID:
    OID: 1.3.6.1.2.1.1.5
    symbol: sysName
    tag: snmp_host
  - # With regular expression matching
    MIB: SNMPv2-MIB
    symbol: sysName
    match: (.*)-(.*)
    tags:
        host: \2
        device_type: \1
```
