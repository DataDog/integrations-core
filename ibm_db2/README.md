# Agent Check: IBM Db2

![default dashboard][1]

## Overview

This check monitors [IBM Db2][2] through the Datadog Agent.

## Setup

### Installation

The IBM Db2 check is included in the [Datadog Agent][3] package.

#### Dependencies

The [ibm_db][4] client library is required. To install it, ensure you have a working compiler and run:

Unix:

```
/opt/datadog-agent/embedded/bin/pip install ibm_db==3.0.1
```

Windows:

```
"C:\Program Files\Datadog\Datadog Agent\embedded\Scripts\python.exe" -m pip install ibm_db==3.0.1
```

Additionally, on Linux there may be need for XML functionality. If you encounter errors during
the build process, install `libxslt-dev` (or `libxslt-devel` for RPM).

#### Privileges

To query metrics from certain tables, specific privileges must be granted to the chosen Db2 user.
Switch to the instance master user and run these commands at the `db2` prompt:

```
update dbm cfg using HEALTH_MON on
update dbm cfg using DFT_MON_STMT on
update dbm cfg using DFT_MON_LOCK on
update dbm cfg using DFT_MON_TABLE on
update dbm cfg using DFT_MON_BUFPOOL on
```

Now if you run `get dbm cfg`, you should see the following:

```
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

1. Edit the `ibm_db2.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your `ibm_db2` performance data. See the [sample ibm_db2.d/conf.yaml][5] for all available configuration options.

2. [Restart the Agent][6].

#### Log Collection

**Available for Agent >6.0**

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

```
logs_enabled: true
```

2. Add this configuration block to your `ibm_db2.d/conf.yaml` file to start collecting your IBM Db2 logs:

```
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

4. [Restart the Agent][6].

### Validation

[Run the Agent's status subcommand][7] and look for `ibm_db2` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this integration.

### Service Checks

- `ibm_db2.can_connect` returns `CRITICAL` if the Agent is unable to connect to
  the monitored IBM Db2 database, otherwise returns `OK`.
- `ibm_db2.status` returns `CRITICAL` if the monitored IBM Db2 database is
  quiesced, `WARNING` for quiesce-pending or rollforwards, otherwise returns `OK`.

### Events

- `ibm_db2.tablespace_state_change` is triggered whenever the state of a tablespace changes.

## Troubleshooting
Need help? Contact [Datadog support][9].

## Further Reading
Additional helpful documentation, links, and articles:

- [Monitor IBM DB2 with Datadog][10]


[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/ibm_db2/assets/images/dashboard_overview.png
[2]: https://www.ibm.com/analytics/us/en/db2
[3]: https://docs.datadoghq.com/agent
[4]: https://github.com/ibmdb/python-ibmdb/tree/master/IBM_DB/ibm_db
[5]: https://github.com/DataDog/integrations-core/blob/master/ibm_db2/datadog_checks/ibm_db2/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-restart-the-agent
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/ibm_db2/metadata.csv
[9]: https://docs.datadoghq.com/help
[10]: https://www.datadoghq.com/blog/monitor-db2-with-datadog/
