# SNMP How-To

## Simulate SNMP devices

SNMP is a protocol for gathering metrics from network devices, but automated testing of the integration would not be practical nor reliable if we used actual devices.

Our approach is to use a simulated SNMP device that responds to SNMP queries using [simulation data](./sim-format.md).

This simulated device is brought up as a Docker container when starting the SNMP test environment using:

```bash
ddev env start snmp [...]
```

## Test SNMP profiles locally

Once the environment is up and running, you can modify the instance configuration to test profiles that support simulated metrics.

The following is an example of an instance configured to use the Cisco Nexus profile.

```yaml
init_config:
  profiles:
    cisco_nexus:
      definition_file: cisco-nexus.yaml

instances:
- community_string: cisco_nexus  # (1.)
  ip_address: <IP_ADDRESS_OF_SNMP_CONTAINER>  # (2.)
  profile: cisco_nexus
  name: localhost
  port: 1161
```

1. The `community_string` must match the corresponding device `.snmprec` file name. For example, `myprofile.snmprec` gives `community_string: myprofile`. This also applies to [walk files](#generate-simulation-data-from-a-walk): `myprofile.snmpwalk` gives `community_string: myprofile`.
2. To find the IP address of the SNMP container, run:

```bash
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' dd-snmp
```

## Run SNMP queries

With the test environment is up and running, we can issue SNMP queries to the simulated device using a command line SNMP client.

### Prerequisites

Make sure you have the Net-SNMP tools installed on your machine. These should come pre-installed by default on Linux and macOS. If necessary, you can download them on the [Net-SNMP website](http://net-snmp.sourceforge.net/download.html).

### Available commands

The Net-SNMP tools provide a number of commands to interact with SNMP devices.

The most commonly used commands are:

- `snmpget`: to issue an SNMP GET query.
- `snmpgetnext`: to issue an SNMP GETNEXT query.
- `snmpwalk`: to query an entire OID sub-tree at once.
- `snmptable`: to query rows in an SNMP table.

### Examples

#### GET query

To query a specific OID from a device, we can use the `snmpget` command.

For example, the following command will query `sysDescr` OID of an SNMP device, which returns its human-readable description:

```console
$ snmpget -v 2c -c public -IR 127.0.0.1:1161 system.sysDescr.0
SNMPv2-MIB::sysDescr.0 = STRING: Linux 41ba948911b9 4.9.87-linuxkit-aufs #1 SMP Wed Mar 14 15:12:16 UTC 2018 x86_64
SNMPv2-MIB::sysORUpTime.1 = Timeticks: (9) 0:00:00.09
```

Let's break this command down:

- `snmpget`: this command sends an SNMP GET request, and can be used to query the value of an OID. Here, we are requesting the `system.sysDescr.0` OID.
- `-v 2c`: instructs your SNMP client to send the request using SNMP version 2c. See [SNMP Versions](introduction.md#snmp-versions).
- `-c public`: instructs the SNMP client to send the community string `public` along with our request. (This is a form of authentication provided by SNMP v2. See [SNMP Versions](introduction.md#snmp-versions).)
- `127.0.0.1:1161`: this is the host and port where the simulated SNMP agent is available at. (Confirm the port used by the ddev environment by inspecting the Docker port mapping via `$ docker ps`.)
- `system.sysDescr.0`: this is the OID that the client should request. In practice this can refer to either a fully-resolved OID (e.g. `1.3.6.1.4.1[...]`), or a label (e.g. `sysDescr.0`).
- `-IR`: this option allows us to use labels for OIDs that aren't in the generic `1.3.6.1.2.1.*` sub-tree (see: [The OID tree](./introduction.md#the-oid-tree)). TL;DR: always use this option when working with OIDs coming from vendor-specific MIBs.

!!! tip
    If the above command fails, try using the explicit OID like so:

    ```console
    $ snmpget -v 2c -c public -IR 127.0.0.1:1161 iso.3.6.1.2.1.1.1.0
    ```

#### Table query

For tables, use the `snmptable` command, which will output the rows in the table in a tabular format. Its arguments and options are similar to `snmpget`.

```console
$ snmptable -v 2c -c public -IR -Os 127.0.0.1:1161 hrStorageTable
SNMP table: hrStorageTable

 hrStorageIndex          hrStorageType    hrStorageDescr hrStorageAllocationUnits hrStorageSize hrStorageUsed hrStorageAllocationFailures
              1           hrStorageRam   Physical memory               1024 Bytes       2046940       1969964                           ?
              3 hrStorageVirtualMemory    Virtual memory               1024 Bytes       3095512       1969964                           ?
              6         hrStorageOther    Memory buffers               1024 Bytes       2046940         73580                           ?
              7         hrStorageOther     Cached memory               1024 Bytes       1577648       1577648                           ?
              8         hrStorageOther     Shared memory               1024 Bytes          2940          2940                           ?
             10 hrStorageVirtualMemory        Swap space               1024 Bytes       1048572             0                           ?
             33     hrStorageFixedDisk              /dev               4096 Bytes         16384             0                           ?
             36     hrStorageFixedDisk    /sys/fs/cgroup               4096 Bytes        255867             0                           ?
             52     hrStorageFixedDisk  /etc/resolv.conf               4096 Bytes      16448139       6493059                           ?
             53     hrStorageFixedDisk     /etc/hostname               4096 Bytes      16448139       6493059                           ?
             54     hrStorageFixedDisk        /etc/hosts               4096 Bytes      16448139       6493059                           ?
             55     hrStorageFixedDisk          /dev/shm               4096 Bytes         16384             0                           ?
             61     hrStorageFixedDisk       /proc/kcore               4096 Bytes         16384             0                           ?
             62     hrStorageFixedDisk        /proc/keys               4096 Bytes         16384             0                           ?
             63     hrStorageFixedDisk  /proc/timer_list               4096 Bytes         16384             0                           ?
             64     hrStorageFixedDisk /proc/sched_debug               4096 Bytes         16384             0                           ?
             65     hrStorageFixedDisk     /sys/firmware               4096 Bytes        255867             0                           ?
```

(In this case, we added the `-Os` option which prints only the last symbolic element and reduces the output of `hrStorageTypes`.)

#### Walk query

A walk query can be used to query all OIDs in a given [sub-tree](./introduction.md#the-oid-tree).

The `snmpwalk` command can be used to perform a walk query.

To facilitate usage of walk files for debugging, the following options are recommended: `-ObentU`. Here's what each option does:

- `b`: do not break OID indexes down.
- `e`: print enums numerically (for example, `24` instead of `softwareLoopback(24)`).
- `n`: print OIDs numerically (for example, `.1.3.6.1.2.1.2.2.1.1.1` instead of `IF-MIB::ifIndex.1`).
- `t`: print timeticks numerically (for example, `4226041` instead of `Timeticks: (4226041) 11:44:20.41`).
- `U`: don't print units.

For example, the following command gets a walk of the `1.3.6.1.2.1.1` (`system`) sub-tree:

```console
$ snmpwalk -v 2c -c public -ObentU 127.0.0.1:1161 1.3.6.1.2.1.1
.1.3.6.1.2.1.1.1.0 = STRING: Linux 41ba948911b9 4.9.87-linuxkit-aufs #1 SMP Wed Mar 14 15:12:16 UTC 2018 x86_64
.1.3.6.1.2.1.1.2.0 = OID: .1.3.6.1.4.1.8072.3.2.10
.1.3.6.1.2.1.1.3.0 = 4226041
.1.3.6.1.2.1.1.4.0 = STRING: root@localhost
.1.3.6.1.2.1.1.5.0 = STRING: 41ba948911b9
.1.3.6.1.2.1.1.6.0 = STRING: Unknown
.1.3.6.1.2.1.1.8.0 = 9
.1.3.6.1.2.1.1.9.1.2.1 = OID: .1.3.6.1.6.3.11.3.1.1
.1.3.6.1.2.1.1.9.1.2.2 = OID: .1.3.6.1.6.3.15.2.1.1
.1.3.6.1.2.1.1.9.1.2.3 = OID: .1.3.6.1.6.3.10.3.1.1
.1.3.6.1.2.1.1.9.1.2.4 = OID: .1.3.6.1.6.3.1
.1.3.6.1.2.1.1.9.1.2.5 = OID: .1.3.6.1.2.1.49
.1.3.6.1.2.1.1.9.1.2.6 = OID: .1.3.6.1.2.1.4
.1.3.6.1.2.1.1.9.1.2.7 = OID: .1.3.6.1.2.1.50
.1.3.6.1.2.1.1.9.1.2.8 = OID: .1.3.6.1.6.3.16.2.2.1
.1.3.6.1.2.1.1.9.1.2.9 = OID: .1.3.6.1.6.3.13.3.1.3
.1.3.6.1.2.1.1.9.1.2.10 = OID: .1.3.6.1.2.1.92
.1.3.6.1.2.1.1.9.1.3.1 = STRING: The MIB for Message Processing and Dispatching.
.1.3.6.1.2.1.1.9.1.3.2 = STRING: The management information definitions for the SNMP User-based Security Model.
.1.3.6.1.2.1.1.9.1.3.3 = STRING: The SNMP Management Architecture MIB.
.1.3.6.1.2.1.1.9.1.3.4 = STRING: The MIB module for SNMPv2 entities
.1.3.6.1.2.1.1.9.1.3.5 = STRING: The MIB module for managing TCP implementations
.1.3.6.1.2.1.1.9.1.3.6 = STRING: The MIB module for managing IP and ICMP implementations
.1.3.6.1.2.1.1.9.1.3.7 = STRING: The MIB module for managing UDP implementations
.1.3.6.1.2.1.1.9.1.3.8 = STRING: View-based Access Control Model for SNMP.
.1.3.6.1.2.1.1.9.1.3.9 = STRING: The MIB modules for managing SNMP Notification, plus filtering.
.1.3.6.1.2.1.1.9.1.3.10 = STRING: The MIB module for logging SNMP Notifications.
.1.3.6.1.2.1.1.9.1.4.1 = 9
.1.3.6.1.2.1.1.9.1.4.2 = 9
.1.3.6.1.2.1.1.9.1.4.3 = 9
.1.3.6.1.2.1.1.9.1.4.4 = 9
.1.3.6.1.2.1.1.9.1.4.5 = 9
.1.3.6.1.2.1.1.9.1.4.6 = 9
.1.3.6.1.2.1.1.9.1.4.7 = 9
.1.3.6.1.2.1.1.9.1.4.8 = 9
.1.3.6.1.2.1.1.9.1.4.9 = 9
.1.3.6.1.2.1.1.9.1.4.10 = 9
```

As you can see, all OIDs that the device has available in the `.1.3.6.1.2.1.1.*` sub-tree are returned. In particular, one can recognize:

- `sysObjectID` (`.1.3.6.1.2.1.1.2.0 = OID: .1.3.6.1.4.1.8072.3.2.10`)
- `sysUpTime` (`.1.3.6.1.2.1.1.3.0 = 4226041`)
- `sysName` (`.1.3.6.1.2.1.1.5.0 = STRING: 41ba948911b9`).

Here is another example that queries the entire contents of `ifTable` (the table in `IF-MIB` that contains information about network interfaces):

```console
snmpwalk -v 2c -c public -OentU 127.0.0.1:1161 1.3.6.1.2.1.2.2
.1.3.6.1.2.1.2.2.1.1.1 = INTEGER: 1
.1.3.6.1.2.1.2.2.1.1.90 = INTEGER: 90
.1.3.6.1.2.1.2.2.1.2.1 = STRING: lo
.1.3.6.1.2.1.2.2.1.2.90 = STRING: eth0
.1.3.6.1.2.1.2.2.1.3.1 = INTEGER: 24
.1.3.6.1.2.1.2.2.1.3.90 = INTEGER: 6
.1.3.6.1.2.1.2.2.1.4.1 = INTEGER: 65536
.1.3.6.1.2.1.2.2.1.4.90 = INTEGER: 1500
.1.3.6.1.2.1.2.2.1.5.1 = Gauge32: 10000000
.1.3.6.1.2.1.2.2.1.5.90 = Gauge32: 4294967295
.1.3.6.1.2.1.2.2.1.6.1 = STRING:
.1.3.6.1.2.1.2.2.1.6.90 = STRING: 2:42:ac:11:0:2
.1.3.6.1.2.1.2.2.1.7.1 = INTEGER: 1
.1.3.6.1.2.1.2.2.1.7.90 = INTEGER: 1
.1.3.6.1.2.1.2.2.1.8.1 = INTEGER: 1
.1.3.6.1.2.1.2.2.1.8.90 = INTEGER: 1
.1.3.6.1.2.1.2.2.1.9.1 = 0
.1.3.6.1.2.1.2.2.1.9.90 = 0
.1.3.6.1.2.1.2.2.1.10.1 = Counter32: 5300203
.1.3.6.1.2.1.2.2.1.10.90 = Counter32: 2928
.1.3.6.1.2.1.2.2.1.11.1 = Counter32: 63808
.1.3.6.1.2.1.2.2.1.11.90 = Counter32: 40
.1.3.6.1.2.1.2.2.1.12.1 = Counter32: 0
.1.3.6.1.2.1.2.2.1.12.90 = Counter32: 0
.1.3.6.1.2.1.2.2.1.13.1 = Counter32: 0
.1.3.6.1.2.1.2.2.1.13.90 = Counter32: 0
.1.3.6.1.2.1.2.2.1.14.1 = Counter32: 0
.1.3.6.1.2.1.2.2.1.14.90 = Counter32: 0
.1.3.6.1.2.1.2.2.1.15.1 = Counter32: 0
.1.3.6.1.2.1.2.2.1.15.90 = Counter32: 0
.1.3.6.1.2.1.2.2.1.16.1 = Counter32: 5300203
.1.3.6.1.2.1.2.2.1.16.90 = Counter32: 0
.1.3.6.1.2.1.2.2.1.17.1 = Counter32: 63808
.1.3.6.1.2.1.2.2.1.17.90 = Counter32: 0
.1.3.6.1.2.1.2.2.1.18.1 = Counter32: 0
.1.3.6.1.2.1.2.2.1.18.90 = Counter32: 0
.1.3.6.1.2.1.2.2.1.19.1 = Counter32: 0
.1.3.6.1.2.1.2.2.1.19.90 = Counter32: 0
.1.3.6.1.2.1.2.2.1.20.1 = Counter32: 0
.1.3.6.1.2.1.2.2.1.20.90 = Counter32: 0
.1.3.6.1.2.1.2.2.1.21.1 = Gauge32: 0
.1.3.6.1.2.1.2.2.1.21.90 = Gauge32: 0
.1.3.6.1.2.1.2.2.1.22.1 = OID: .0.0
.1.3.6.1.2.1.2.2.1.22.90 = OID: .0.0
```

## Generate table simulation data

To generate [simulation data for tables](./sim-format.md#tables) automatically, use the [`mib2dev.py`](https://github.com/etingof/snmpsim/blob/master/docs/source/documentation/building-simulation-data.rst#examples) tool shipped with `snmpsim`. This tool will be renamed as `snmpsim-record-mibs` in the upcoming 1.0 release of the library.

First, install snmpsim:

```bash
pip install snmpsim
```

Then run the tool, specifying the MIB with the start and stop OIDs (which can correspond to .e.g the first and last columns in the table respectively).

For example:

```bash
mib2dev.py --mib-module=<MIB> --start-oid=1.3.6.1.4.1.674.10892.1.400.20 --stop-oid=1.3.6.1.4.1.674.10892.1.600.12 > /path/to/mytable.snmprec
```

The following command generates 4 rows for the `IF-MIB:ifTable (1.3.6.1.2.1.2.2)`:

```bash
mib2dev.py --mib-module=IF-MIB --start-oid=1.3.6.1.2.1.2.2 --stop-oid=1.3.6.1.2.1.2.3 --table-size=4 > /path/to/mytable.snmprec
```

### Known issues
`mib2dev` has a known issue with `IF-MIB::ifPhysAddress`, that is expected to contain an hexadecimal string, but `mib2dev` fills it with a string. To fix this, provide a valid hextring when prompted on the command line:

```bash
# Synthesizing row #1 of table 1.3.6.1.2.1.2.2.1
*** Inconsistent value: Display format eval failure: b'driving kept zombies quaintly forward zombies': invalid literal for int() with base 16: 'driving kept zombies quaintly forward zombies'caused by <class 'ValueError'>: invalid literal for int() with base 16: 'driving kept zombies quaintly forward zombies'
*** See constraints and suggest a better one for:
# Table IF-MIB::ifTable
# Row IF-MIB::ifEntry
# Index IF-MIB::ifIndex (type InterfaceIndex)
# Column IF-MIB::ifPhysAddress (type PhysAddress)
# Value ['driving kept zombies quaintly forward zombies'] ? 001122334455
```

## Generate simulation data from a walk

As an alternative to [`.snmprec` files](./sim-format.md), it is possible to [use a walk as simulation data](http://snmplabs.com/snmpsim/documentation/building-simulation-data.html#using-snmpwalk-reporting). This is especially useful when debugging live devices, since you can export the device walk and use this real data locally.

To do so, paste the output of a [walk query](#walk-query) into a `.snmpwalk` file, and add this file to the test data directory. Then, pass the name of the walk file as the `community_string`. For more information, see [Test SNMP profiles locally](#test-snmp-profiles-locally).

## Find where MIBs are installed on your machine

See the [Using and loading MIBs](http://net-snmp.sourceforge.net/wiki/index.php/TUT:Using_and_loading_MIBS) Net-SNMP tutorial.

## Browse locally installed MIBs

Since [community resources](./introduction.md#tools-and-resources) that list MIBs and OIDs are best effort, the MIB you are investigating may not be present or may not be available in its the latest version.

In that case, you can use the [`snmptranslate`](http://net-snmp.sourceforge.net/tutorial/tutorial-5/commands/snmptranslate.html) CLI tool to output similar information for MIBs installed on your system. This tool is part of Net-SNMP - see [SNMP queries prerequisites](#prerequisites).

**Steps**

1. Run `$ snmptranslate -m <MIBNAME> -Tz -On` to get a complete list of OIDs in the `<MIBNAME>` MIB along with their labels.
2. Redirect to a file for nicer formatting as needed.

Example:

```console
$ snmptranslate -m IF-MIB -Tz -On > out.log
$ cat out.log
"org"                   "1.3"
"dod"                   "1.3.6"
"internet"                      "1.3.6.1"
"directory"                     "1.3.6.1.1"
"mgmt"                  "1.3.6.1.2"
"mib-2"                 "1.3.6.1.2.1"
"system"                        "1.3.6.1.2.1.1"
"sysDescr"                      "1.3.6.1.2.1.1.1"
"sysObjectID"                   "1.3.6.1.2.1.1.2"
"sysUpTime"                     "1.3.6.1.2.1.1.3"
"sysContact"                    "1.3.6.1.2.1.1.4"
"sysName"                       "1.3.6.1.2.1.1.5"
"sysLocation"                   "1.3.6.1.2.1.1.6"
[...]
```

!!! tip
    Use the `-M <DIR>` option to specify the directory where `snmptranslate` should look for MIBs. Useful if you want to inspect a MIB you've just downloaded but not moved to the default MIB directory.

!!! tip
    Use `-Tp` for an alternative tree-like formatting.
