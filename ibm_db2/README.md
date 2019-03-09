# Agent Check: IBM Db2

## Overview

This check monitors [IBM Db2][1] through the Datadog Agent.

## Setup

### Installation

The IBM Db2 check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

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

1. Edit the `ibm_db2.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your `ibm_db2` performance data. See the [sample ibm_db2.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3].

### Validation

[Run the Agent's status subcommand][4] and look for `ibm_db2` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

### Service Checks

- `ibm_db2.can_connect` returns `CRITICAL` if the Agent is unable to connect to
  the monitored IBM Db2 database, or `OK` otherwise.
- `ibm_db2.status` returns `CRITICAL` if the monitored IBM Db2 database is
  quiesced, `WARNING` for quiesce-pending or rollforwards, or `OK` otherwise.

### Events

- `ibm_db2.tablespace_state_change` is triggered whenever the state of a tablespace changes.

## Troubleshooting

Need help? Contact [Datadog support][6].

[1]: https://www.ibm.com/analytics/us/en/db2
[2]: https://github.com/DataDog/integrations-core/blob/master/ibm_db2/datadog_checks/ibm_db2/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/ibm_db2/metadata.csv
[6]: https://docs.datadoghq.com/help
