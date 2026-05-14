# Agent Check: DO Query Actions

## Overview

The DO Query Actions check executes SQL queries against PostgreSQL and reports success/failure metrics. This check is designed to receive configuration via Remote Config and execute queries on demand.

## Setup

### Installation

The DO Query Actions check is included in the Datadog Agent package.

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
| `do_query_actions.query_status` | gauge | 1 if query succeeded, 0 if failed |

### Service Checks

No service checks are provided by this integration.

### Events

Query results are sent as events via the `do-query-results` event track type, containing query output, execution metadata, and entity information.

## Troubleshooting

Need help? Contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
