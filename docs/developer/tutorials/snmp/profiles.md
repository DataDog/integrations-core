# Build an SNMP Profile

SNMP profiles are our way of providing out-of-the-box monitoring for certain makes and models of network devices.

This tutorial will walk you through the steps of building a basic SNMP profile that collects OID metrics from HP iLO4 devices.

Feel free to read the [Introduction to SNMP](./introduction.md) if you need a refresher on SNMP concepts such as OIDs and MIBs.

Ready? Let's get started!

## Research

The first step to building an SNMP profile is doing some basic research about the device, and which metrics we want to collect.

### General device information

Generally, you'll want to search the web and find out about the following:

- Device name, manufacturer, and device `sysobjectid`.

- Understand what the device does, and what it is used for. (Which metrics are relevant varies between routers, switches, bridges, etc. See [Networking hardware](https://en.wikipedia.org/wiki/Networking_hardware).)

    > E.g. from the [HP iLO Wikipedia page](https://en.wikipedia.org/wiki/HP_Integrated_Lights-Out), we can see that iLO4 devices are used by system administrators for remote management of embedded servers.

- Available versions of the device, and which ones we target.

    > E.g. HP iLO devices exist in multiple versions (version 3, version 4...). Here, we are specifically targeting HP iLO4.

- Supported MIBs and OIDs (often available in official documentation), and associated MIB files.

    > E.g. we can see that HP provides a MIB package for iLO devices [here](https://support.hpe.com/hpsc/swd/public/detail?swItemId=MTX_53293d026fb147958b223069b6).

### Metrics selection

Now that we have gathered some basic information about the device and its SNMP interfaces, we should decide which metrics we want to collect. (Devices often expose thousands of metrics through SNMP. We certainly don't want to collect them all.)

Devices typically expose thousands of OIDs that can span dozens of MIB, so this can feel daunting at first. Remember, [never give up!](https://www.youtube.com/watch?v=KxGRhd_iWuE)

Some guidelines to help you in this process:

- 10-40 metrics is a good amount already.
- Explore base profiles to see which ones could be applicable to the device.
- Explore manufacturer-specific MIB files looking for metrics such as:
    - General health: status gauges...
    - Network traffic: bytes in/out, errors in/out, ...
    - CPU and memory usage.
    - Temperature: temperature sensors, thermal condition, ...
    - Power supply.
    - Storage.
    - Field-replaceable units ([FRU](https://en.wikipedia.org/wiki/Field-replaceable_unit)).
    - ...

## Implementation

It might be tempting to gather as many metrics as possible, and only then start building the profile and writing tests.

But we recommend you **start small**. This will allow you to quickly gain confidence on the various components of the SNMP development workflow:

- Editing profile files.
- Writing tests.
- Building and using simulation data.

### Add a profile file

Add a `.yaml` file for the profile with the `sysobjectid` and a metric (you'll be able to add more later).

For example:

```yaml
sysobjectid: 1.3.6.1.4.1.232.9.4.10

metrics:
  - MIB: CPQHLTH-MIB
    symbol:
      OID: 1.3.6.1.4.1.232.6.2.8.1.0
      name: cpqHeSysUtilLifeTime
```

!!! tip
    `sysobjectid` can also be a wildcard pattern to match a sub-tree of devices, eg `1.3.6.1.131.12.4.*`.

### Generate a profile file from a collection of MIBs

You can use `ddev` to create a profile from a list of mibs.

```console
$  ddev meta snmp generate-profile-from-mibs --help
```

This script requires a list of ASN1 MIB files as input argument, and copies to the clipboard a list of metrics that can be used to create a profile.

#### Options

`-f, --filters` is an option to provide the path to a YAML file containing a collection of MIB names and their list of node names to be included.

For example:

```yaml
RFC1213-MIB:
- system
- interfaces
- ip
CISCO-SYSLOG-MIB: []
SNMP-FRAMEWORK-MIB:
- snmpEngine
```

Will include `system`, `interfaces` and `ip` nodes from `RFC1213-MIB`, no node from `CISCO-SYSLOG-MIB`, and node `snmpEngine` from `SNMP-FRAMEWORK-MIB`.

Note that each `MIB:node_name` correspond to exactly one and only one OID. However, some MIBs report legacy nodes that are overwritten.

To resolve, edit the MIB by removing legacy values manually before loading them with this profile generator. If a MIB is fully supported, it can be omitted from the filter as MIBs not found in a filter will be fully loaded. If a MIB is *not* fully supported, it can be listed with an empty node list, as `CISCO-SYSLOG-MIB` in the example.

`-a, --aliases` is an option to provide the path to a YAML file containing a list of aliases to be used as metric tags for tables, in the following format:

```yaml
aliases:
- from:
    MIB: ENTITY-MIB
    name: entPhysicalIndex
  to:
    MIB: ENTITY-MIB
    name: entPhysicalName
```

MIBs tables most of the time define one or more indexes, as columns within the same table, or columns from a different table and even a different MIB. The index value can be used to tag table's metrics. This is defined in the `INDEX` field in `row` nodes.

As an example, `entPhysicalContainsTable` in `ENTITY-MIB` is as follows:

```txt
entPhysicalContainsEntry OBJECT-TYPE
SYNTAX      EntPhysicalContainsEntry
MAX-ACCESS  not-accessible
STATUS      current
DESCRIPTION
        "A single container/'containee' relationship."
INDEX       { entPhysicalIndex, entPhysicalChildIndex }  <== this is the index definition
::= { entPhysicalContainsTable 1 }
```

or its JSON dump, where `INDEX` is replaced by `indices`:

```json
"entPhysicalContainsEntry": {
    "name": "entPhysicalContainsEntry",
    "oid": "1.3.6.1.2.1.47.1.3.3.1",
    "nodetype": "row",
    "class": "objecttype",
    "maxaccess": "not-accessible",
    "indices": [
      {
        "module": "ENTITY-MIB",
        "object": "entPhysicalIndex",
        "implied": 0
      },
      {
        "module": "ENTITY-MIB",
        "object": "entPhysicalChildIndex",
        "implied": 0
      }
    ],
    "status": "current",
    "description": "A single container/'containee' relationship."
  },
```

Indexes can be replaced by another MIB symbol that is more human friendly. You might prefer to see the interface name versus its numerical table index. This can be achieved using `metric_tag_aliases`.

### Add unit tests

Add a unit test in `test_profiles.py` to verify that the metric is successfully collected by the integration when the profile is enabled. (These unit tests are mostly used to prevent regressions and will help with maintenance.)

For example:

```python
def test_hp_ilo4(aggregator):
    run_profile_check('hp_ilo4')

    common_tags = common.CHECK_TAGS + ['snmp_profile:hp-ilo4']

    aggregator.assert_metric('snmp.cpqHeSysUtilLifeTime', metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1)
    aggregator.assert_all_metrics_covered()
```

We don't have simulation data yet, so the test should fail. Let's make sure it does:

```console
$ ddev test -k test_hp_ilo4 snmp:py38
[...]
======================================= FAILURES ========================================
_____________________________________ test_hp_ilo4 ______________________________________
tests/test_profiles.py:1464: in test_hp_ilo4
    aggregator.assert_metric('snmp.cpqHeSysUtilLifeTime', metric_type=aggregator.GAUGE, tags=common.CHECK_TAGS, count=1)
../datadog_checks_base/datadog_checks/base/stubs/aggregator.py:253: in assert_metric
    self._assert(condition, msg=msg, expected_stub=expected_metric, submitted_elements=self._metrics)
../datadog_checks_base/datadog_checks/base/stubs/aggregator.py:295: in _assert
    assert condition, new_msg
E   AssertionError: Needed exactly 1 candidates for 'snmp.cpqHeSysUtilLifeTime', got 0
[...]
```

Good. Now, onto adding simulation data.

### Add simulation data

Add a `.snmprec` file named after the `community_string`, which is the value we gave to `run_profile_check()`:

```
$ touch snmp/tests/compose/data/hp_ilo4.snmprec
```

Add lines to the `.snmprec` file to specify the `sysobjectid` and the OID listed in the profile:

```console
1.3.6.1.2.1.1.2.0|6|1.3.6.1.4.1.232.9.4.10
1.3.6.1.4.1.232.6.2.8.1.0|2|1051200
```

Run the test again, and make sure it passes this time:

```console
$ ddev test -k test_hp_ilo4 snmp:py38
[...]

tests/test_profiles.py::test_hp_ilo4 PASSED                                                                                        [100%]

=================================================== 1 passed, 107 deselected in 9.87s ====================================================
________________________________________________________________ summary _________________________________________________________________
  py38: commands succeeded
  congratulations :)
```

### Rinse and repeat

We have now covered the basic workflow — add metrics, expand tests, add simulation data. You can now go ahead and add more metrics to the profile!

## Next steps

Congratulations! You should now be able to write a basic SNMP profile.

We kept this tutorial as simple as possible, but profiles offer many more options to collect metrics from SNMP devices.

- To learn more about what can be done in profiles, read the [Profile format reference](./profile-format.md).
- To learn more about `.snmprec` files, see the [Simulation data format reference](./sim-format.md).
