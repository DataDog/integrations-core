# Agent Check: IBM Db2

![default dashboard][1]

## Overview

This check monitors [IBM Db2][2] through the Datadog Agent.

**Minimum Agent version:** 6.11.0

## Setup

### Installation

The IBM Db2 check is included in the [Datadog Agent][3] package.

#### Dependencies

The [ibm_db][4] client library is required. To install it, ensure you have a working compiler and run:

##### Unix

```text
sudo -Hu dd-agent /opt/datadog-agent/embedded/bin/pip install ibm_db==3.2.6
```

Note: If you are on an Agent running Python 2, use `ibm_db==3.0.1` instead of `ibm_db==3.2.6`.

##### Windows

For Agent versions <= 6.11:

```text
"C:\Program Files\Datadog\Datadog Agent\embedded\python.exe" -m pip install ibm_db==3.0.1
```

For Agent versions >= 6.12 and < 7.0:

```text
"C:\Program Files\Datadog\Datadog Agent\embedded<PYTHON_MAJOR_VERSION>\python.exe" -m pip install ibm_db==3.0.1
```

For Agent versions >= 7.0 and < 7.58:

```text
"C:\Program Files\Datadog\Datadog Agent\embedded3\python.exe" -m pip install ibm_db==3.1.4
```

For Agent versions >= 7.58:

```text
"C:\Program Files\Datadog\Datadog Agent\embedded3\python.exe" -m pip install ibm_db==3.2.6
```

On Linux there may be need for XML functionality. If you encounter errors during
the build process, install `libxslt-dev` (or `libxslt-devel` for RPM).

#### Prepare IBM DB2

As a best practice, Datadog recommends creating the machine user with read-only access to limit the permissions granted to the Datadog Agent.

#### Enable monitoring

The IBM Db2 integration pulls data using the following table functions:
* `MON_GET_TABLESPACE`
* `MON_GET_TRANSACTION_LOG`
* `MON_GET_BUFFERPOOL`
* `MON_GET_DATABASE`
* `MON_GET_INSTANCE`

For more information about these table functions, see the [official IBM documentation][17].

To monitor a Db2 instance, create a Db2 user with either the `EXECUTE` permission on the above five table functions, or grant the Db2 user one of the following roles:
* `DATAACCESS` authority
* `DBADM` authority
* `SQLADM` authority

To monitor the health of an instance, its associated databases, and database objects, enable the database system monitor switches for each of the objects you want to monitor:
* Statement
* Lock
* Tables
* Buffer pool

Switch to the instance master user and run these commands at the `db2` prompt:

```text
update dbm cfg using HEALTH_MON on
update dbm cfg using DFT_MON_STMT on
update dbm cfg using DFT_MON_LOCK on
update dbm cfg using DFT_MON_TABLE on
update dbm cfg using DFT_MON_BUFPOOL on
```

Next, run `get dbm cfg` and you should see the following:

```text
 Default database monitor switches
   Buffer pool                         (DFT_MON_BUFPOOL) = ON
   Lock                                   (DFT_MON_LOCK) = ON
   Sort                                   (DFT_MON_SORT) = OFF
   Statement                              (DFT_MON_STMT) = ON
   Table                                 (DFT_MON_TABLE) = ON
   Timestamp                         (DFT_MON_TIMESTAMP) = ON
   Unit of work                            (DFT_MON_UOW) = OFF
 Monitor health of instance and databases   (HEALTH_MON) = ON
```

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

##### Metric collection

1. Edit the `ibm_db2.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your `ibm_db2` performance data. See the [sample ibm_db2.d/conf.yaml][5] for all available configuration options.

2. [Restart the Agent][6].

##### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `ibm_db2.d/conf.yaml` file to start collecting your IBM Db2 logs:

   ```yaml
   logs:
     - type: file
       path: /home/db2inst1/sqllib/db2dump/db2diag.log
       source: ibm_db2
       service: db2sysc
       log_processing_rules:
         - type: multi_line
           name: new_log_start_with_date
           pattern: \d{4}\-(0?[1-9]|[12][0-9]|3[01])\-(0?[1-9]|1[012])
   ```

3. [Restart the Agent][6].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][7] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                                                                                         |
| -------------------- | ------------------------------------------------------------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `ibm_db2`                                                                                                     |
| `<INIT_CONFIG>`      | blank or `{}`                                                                                                 |
| `<INSTANCE_CONFIG>`  | `{"db": "<DB_NAME>", "username":"<USERNAME>", "password":"<PASSWORD>", "host":"%%host%%", "port":"%%port%%"}` |

##### Log collection

_Available for Agent versions >6.0_

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][8].

| Parameter      | Value                                                                                                                                                                                                |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "ibm_db2", "service": "<SERVICE_NAME>", "log_processing_rules": {"type":"multi_line","name":"new_log_start_with_date", "pattern":"\d{4}\-(0?[1-9]|[12][0-9]|3[01])\-(0?[1-9]|1[012])"}}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Database Monitoring

**Note**: Database Monitoring for IBM Db2 is in Preview. To request access, contact your Datadog account team.

Database Monitoring (`dbm: true`) collects query execution counts, elapsed time, CPU time,
rows read and returned, lock waits, and obfuscated SQL from each database's package cache.
Configure each database you want to monitor separately.

#### Connect to a fixed server

Configure exactly one check instance for each database on each monitored server. The Agent
can run on the database server or remotely. Its connection must always reach the same
server, including after a failover:

- Set `host` and `port` to the server's direct address. Do not use a primary-following
  virtual IP, load balancer, or DNS name that switches between servers.
- Disable automatic client reroute for the Agent's IBM driver connections, as described below.
- Keep each server's host identity stable when its primary or standby role changes.
  Do not use a shared cluster identity for both servers.
- Do not configure another Agent or check instance to collect the same database on that server.

For example, one Agent monitoring two servers uses:

```yaml
instances:
  - db: appdb
    host: db2-a.example.com
    port: 50000
    username: datadog
    password: <PASSWORD>
    dbm: true

  - db: appdb
    host: db2-b.example.com
    port: 50000
    username: datadog
    password: <PASSWORD>
    dbm: true
```

If each server runs its own Agent, put only that server's entry in its configuration.
See the [sample configuration][5] for collection intervals, query timeouts, and other options.

#### Database permissions

Query metrics require `EXECUTE` permission on `SYSPROC.MON_GET_PKG_CACHE_STMT`, in
addition to the integration's monitoring permissions above. If the monitoring user does
not already have an authority that grants access, run this in each monitored database:

```sql
GRANT EXECUTE ON FUNCTION SYSPROC.MON_GET_PKG_CACHE_STMT TO USER <DATADOG_USER>;
```

#### Disable automatic client reroute

A direct address alone does not prevent the IBM driver from using an alternate server.
In the `db2dsdriver.cfg` used by the Agent's IBM CLI driver, disable automatic client
reroute (ACR) for each configured database, host, and port:

```xml
<configuration>
  <databases>
    <database name="appdb" host="db2-a.example.com" port="50000">
      <acr>
        <parameter name="enableAcr" value="false"/>
        <parameter name="enableAlternateServerListFirstConnect" value="false"/>
      </acr>
    </database>
    <database name="appdb" host="db2-b.example.com" port="50000">
      <acr>
        <parameter name="enableAcr" value="false"/>
        <parameter name="enableAlternateServerListFirstConnect" value="false"/>
      </acr>
    </database>
  </databases>
</configuration>
```

Apply these settings to the Agent's driver configuration, not your application's driver
configuration. Set `DB2DSDRIVER_CFG_PATH` in the Agent process environment to the absolute
path of this file, or use the driver's [default configuration location][19]. Restart the
Agent after changing it. See [IBM's client reroute configuration documentation][18] for details.

**Note**: If `enableAlternateServerListFirstConnect` is `true`, the driver can reroute even
when other ACR settings disable rerouting. Set both parameters to `false`.

#### High availability disaster recovery (HADR)

Use the same fixed-server configuration for an HADR pair. Each collector reports queries
executed on its own server; replication does not make a standby's query counters a copy
of the primary's counters. A readable standby can report its own read workload. A standby
without reads enabled cannot accept the SQL connections required for query metrics.

During takeover, the collectors stay on their configured servers. Workload moves to the
new primary, so Datadog reports those queries under the new primary's identity. The old
primary retains its identity and can report its subsequent read workload if it becomes a
readable standby. Connections can drop during the transition. Collection resumes when the
server accepts SQL connections again.

Query metrics use differences between cumulative package-cache counters. New cache entries
establish a baseline before reporting subsequent executions. The Agent can miss executions
of queries that leave the package cache between collections. Query metrics monitor query
workload only. They do not report replication lag or HADR health, and they do not identify
the current primary.

### Validation

[Run the Agent's status subcommand][9] and look for `ibm_db2` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][10] for a list of metrics provided by this integration.

### Events

- `ibm_db2.tablespace_state_change` is triggered whenever the state of a tablespace changes.

### Service Checks

See [service_checks.json][11] for a list of service checks provided by this integration.

## Troubleshooting

### CLI Driver SQL1531N error

If you encounter an issue that produces error logs like the following:

```
2023-08-10 23:34:47 UTC | CORE | ERROR | (pkg/collector/python/datadog_agent.go:129 in LogMessage) | ibm_db2:c051131490335a94 | (ibm_db2.py:563) | Unable to connect to database `datadog` as user `db2inst1`: [IBM][CLI Driver] SQL1531N  The connection failed because the name specified with the DSN connection string keyword could not be found in either the db2dsdriver.cfg configuration file or the db2cli.ini configuration file.  Data source name specified in the connection string: "DATADOG". SQLCODE=-1531
```

Then it's most likely caused by one of the following scenarios:
- The configuration (conf.yaml) is missing a host and port configuration
- The CLI Driver isn't able to locate the database due to the absence of `db2cli.ini` and `db2dsdriver.cfg`

The Agent requires the information in both of the above scenarios to determine where to properly connect to the database. To solve this issue, you can either include a host and port parameter for every instance of the `ibm_db2` check experiencing this issue. Alternatively, if you want to use the DSNs defined in either the `db2cli.ini` or `db2dsdriver.cfg` files, you can copy those files over to the `clidriver` directory that the Agent uses. Under normal circumstances, that directory is located at `/opt/datadog-agent/embedded/lib/python3.9/site-packages/clidriver/cfg` for Linux.

### Installing `ibm_db` client library offline

If you're in an air gapped environment, or on a restricted network where it's not possible to run `pip install ibm_db==x.y.z` where `x.y.z` is the version number, you can install `ibm_db` using the following method:


1. On a machine with network access, download the source tarballs for [the `ibm_db` library][14] and [the ODBC and CLI][16]. The ODBC and CLI are required to be downloaded separately because the `ibm_db` library requires them, but it cannot download them via `pip`. The following script installs the archive file for `ibm_db==x.y.z` on a Linux machine, where `x.y.z` is the version number:

   ```
   curl -Lo ibm_db.tar.gz https://github.com/ibmdb/python-ibmdb/archive/refs/tags/vx.y.z.tar.gz

   curl -Lo linuxx64_odbc_cli.tar.gz https://public.dhe.ibm.com/ibmdl/export/pub/software/data/db2/drivers/odbc_cli/linuxx64_odbc_cli.tar.gz
   ```

1. Transport the two files over to the restricted host, and then extract the archive.

   ```
   tar -xvf ibm_db.tar.gz

   tar -xvf linuxx64_odbc_cli.tar.gz
   ```

1. Set the `IBM_DB_HOME` environment variable to the location of where `/clidriver` was extracted from `linuxx64_odbc_cli.tar.gz`. This will prevent the `ibm_db` library from installing a new version of the ODBC and CLI since that would fail.

   ```
   export IBM_DB_HOME=/path/to/clidriver
   ```

1. Using the embedded [`pip`][15] on the Agent, install the `ibm_db` library locally. This library's files are contained within the extracted `python-ibmdb-x.y.z` from `ibm_db.tar.gz`.

   ```
   /opt/datadog-agent/embedded/bin/pip install --no-index --no-deps --no-build-isolation  /path/to/python-ibmdb-x.y.z/IBM_DB/ibm_db/
   ```

If you get the following error:

```
  error: subprocess-exited-with-error

  × Preparing metadata (pyproject.toml) did not run successfully.
  | exit code: 1
   -> [8 lines of output]
      Detected 64-bit Python
      Detected platform = linux, uname = x86_64
      Downloading https://public.dhe.ibm.com/ibmdl/export/pub/software/data/db2/drivers/odbc_cli/linuxx64_odbc_cli.tar.gz
       Downloading DSDriver from url =  https://public.dhe.ibm.com/ibmdl/export/pub/software/data/db2/drivers/odbc_cli/linuxx64_odbc_cli.tar.gz
      Pre-requisite check [which gcc] : Failed

      No Gcc installation detected.
      Please install gcc and continue with the installation of the ibm_db.
      [end of output]
```

You may need to install `gcc`.

Need help? Contact [Datadog support][12].

## Further Reading

Additional helpful documentation, links, and articles:

- [Monitor IBM DB2 with Datadog][13]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/ibm_db2/images/dashboard_overview.png
[2]: https://www.ibm.com/analytics/us/en/db2
[3]: /account/settings/agent/latest
[4]: https://github.com/ibmdb/python-ibmdb
[5]: https://github.com/DataDog/integrations-core/blob/master/ibm_db2/datadog_checks/ibm_db2/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-restart-the-agent
[7]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[8]: https://docs.datadoghq.com/agent/kubernetes/log/
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[10]: https://github.com/DataDog/integrations-core/blob/master/ibm_db2/metadata.csv
[11]: https://github.com/DataDog/integrations-core/blob/master/ibm_db2/assets/service_checks.json
[12]: https://docs.datadoghq.com/help/
[13]: https://www.datadoghq.com/blog/monitor-db2-with-datadog
[14]: https://pypi.org/project/ibm-db/#files
[15]: https://docs.datadoghq.com/developers/guide/custom-python-package/?tab=linux
[16]: https://public.dhe.ibm.com/ibmdl/export/pub/software/data/db2/drivers/odbc_cli/
[17]: https://www.ibm.com/docs/en/db2oc?topic=views-monitor-procedures-functions

[18]: https://www.ibm.com/docs/en/db2/12.1.x?topic=njcshacd-configuration-db2-automatic-client-reroute-support-applications-other-than-java
[19]: https://www.ibm.com/docs/en/db2/12.1.x?topic=file-data-server-driver-configuration-location
