# Agent Check: IBM Db2

![default dashboard][1]

## Overview

This check monitors [IBM Db2][2] through the Datadog Agent.

## Setup

### Installation

The IBM Db2 check is included in the [Datadog Agent][3] package.

#### Dependencies

The [ibm_db][4] client library is required. To install it, ensure you have a working compiler and run:

##### Unix

```text
sudo -Hu dd-agent /opt/datadog-agent/embedded/bin/pip install ibm_db==3.0.1
```

##### Windows

For Agent versions <= 6.11:

```text
"C:\Program Files\Datadog\Datadog Agent\embedded\python.exe" -m pip install ibm_db==3.0.1
```

For Agent versions >= 6.12 and < 7.0:

```text
"C:\Program Files\Datadog\Datadog Agent\embedded<PYTHON_MAJOR_VERSION>\python.exe" -m pip install ibm_db==3.0.1
```

For Agent versions >= 7.0:

```text
"C:\Program Files\Datadog\Datadog Agent\embedded3\python.exe" -m pip install ibm_db==3.1.0
```

On Linux there may be need for XML functionality. If you encounter errors during
the build process, install `libxslt-dev` (or `libxslt-devel` for RPM).

#### Enable monitoring

To monitor the health of an instance, its associated databases, and database objects, enable the database system monitor switches for each of the objects you want to monitor: 
* statement
* lock
* tables
* buffer pool

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

Need help? Contact [Datadog support][12].

## Further Reading

Additional helpful documentation, links, and articles:

- [Monitor IBM DB2 with Datadog][13]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/ibm_db2/images/dashboard_overview.png
[2]: https://www.ibm.com/analytics/us/en/db2
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://github.com/ibmdb/python-ibmdb/tree/master/IBM_DB/ibm_db
[5]: https://github.com/DataDog/integrations-core/blob/master/ibm_db2/datadog_checks/ibm_db2/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-restart-the-agent
[7]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[8]: https://docs.datadoghq.com/agent/kubernetes/log/
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[10]: https://github.com/DataDog/integrations-core/blob/master/ibm_db2/metadata.csv
[11]: https://github.com/DataDog/integrations-core/blob/master/ibm_db2/assets/service_checks.json
[12]: https://docs.datadoghq.com/help/
[13]: https://www.datadoghq.com/blog/monitor-db2-with-datadog
