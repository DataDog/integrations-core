# Agent Check: Do Query Actions

## Overview

The Do Query Actions check executes SQL queries against PostgreSQL and reports success/failure metrics. This check is designed to receive configuration via Remote Config and execute queries on demand.

## Setup

### Installation

The Do Query Actions check is included in the Datadog Agent package.

### Dependencies

This check requires database client libraries:

**For PostgreSQL:**
```bash
sudo -Hu dd-agent /opt/datadog-agent/embedded/bin/pip install 'psycopg[c,pool]==3.2.10'
```

**For MySQL:**
```bash
sudo -Hu dd-agent /opt/datadog-agent/embedded/bin/pip install pymysql==1.1.2
```

### Configuration

1. Edit the `do_query_actions.d/conf.yaml` file in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting metrics. See the sample `do_query_actions.d/conf.yaml.example` for all available configuration options.

2. Restart the Agent.

### Validation

Run the Agent's status subcommand and look for `do_query_actions` under the Checks section.

## Data Collected

### Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `do_query_actions.query_execution_time` | gauge | Time taken to execute the query in seconds |
| `do_query_actions.query_success` | gauge | 1 if query succeeded, 0 if failed |
| `do_query_actions.rows_affected` | gauge | Number of rows affected by the query |

### Service Checks

**do_query_actions.query_status**

Returns `CRITICAL` if the query execution fails. Returns `OK` otherwise.

### Events

The Do Query Actions check does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
