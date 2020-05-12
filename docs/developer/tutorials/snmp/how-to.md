# SNMP How-To

## Simulate SNMP devices

SNMP is a protocol for gathering metrics from network devices (e.g. routers, switches, etc.), but we don't have access to actual devices (_yet_).

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
- community_string: cisco_nexus  # (1)
  ip_address: <IP_ADDRESS_OF_SNMP_CONTAINER>  # (2)
  profile: cisco_nexus
  name: localhost
  port: 1161
```

(1) The `community_string` must match the corresponding device `.snmprec` file name.

(2) To find the IP address of the SNMP container, run:

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

### Example: GET query

To query a specific OID from a device, we can use the `snmpget` command.

For example, the following command will query `sysDescr` OID of an SNMP device, which returns its human-readable description:

```console
$ snmpget -v 2c -c public -IR 127.0.0.1:1161 system.sysDescr.0
SNMPv2-MIB::sysDescr.0 = STRING: Linux 41ba948911b9 4.9.87-linuxkit-aufs #1 SMP Wed Mar 14 15:12:16 UTC 2018 x86_64
SNMPv2-MIB::sysORUpTime.1 = Timeticks: (9) 0:00:00.09
```

Let's break this command down:

- `snmpget`: this command sends an SNMP GET request, and can be used to query the value of an OID. Here, we are requesting the `system.sysDescr.0` OID.
- `-v 2c`: instructs your SNMP client to send the request using SNMP version 2c. See [SNMP Versions](#snmp-versions).
- `-c public`: instructs the SNMP client to send the community string `public` along with our request. (This is a form of authentication provided by SNMP v2. See [SNMP Versions](#snmp-versions).)
- `127.0.0.1:1161`: this is the host and port where the simulated SNMP agent is available at. (Confirm the port used by the ddev environment by inspecting the Docker port mapping via `$ docker ps`.)
- `system.sysDescr.0`: this is the OID that the client should request. In practice this can refer to either a fully-resolved OID (e.g. `1.3.6.1.4.1[...]`), or a label (e.g. `sysDescr.0`).
- `-IR`: this option allows us to use labels for OIDs that aren't in the generic `1.3.6.1.2.1.*` sub-tree (see: [The OID tree](./introduction.md#the-oid-tree)). TL;DR: always use this option when working with OIDs coming from vendor-specific MIBs.

!!! tip
    If the above command fails, try using the explicit OID like so:

    ```console
    $ snmpget -v 2c -c public -IR 127.0.0.1:1161 iso.3.6.1.2.1.1.1.0
    ```

### Example: table query

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

## Generate table simulation data

If you'd like to generate [simulation data for tables](./sim-format.md#tables) automatically, you can use the [`mib2dev.py`](http://snmplabs.com/snmpsim/documentation/building-simulation-data.html?highlight=snmpsim-record-mibs#examples) tool shipped with `snmpsim`. (This tool will be renamed as `snmpsim-record-mibs` in the upcoming 1.0 release of the library.)

First, install snmpsim:

```bash
pip install snmpsim
```

Then run the tool, specifying the MIB, and start and stop OIDs (which can correspond to .e.g the first and last columns in the table respectively).

For example:

```bash
mib2dev.py --mib-module=<MIB> --start-oid=1.3.6.1.4.1.674.10892.1.400.20 --stop-oid=1.3.6.1.4.1.674.10892.1.600.12 > /path/to/mytable.snmprec
```

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
