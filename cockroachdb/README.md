# Agent Check: CockroachDB

## Overview

The CockroachDB check monitors the overall health and performance of a [CockroachDB][1] cluster.

## Setup

### Installation

The CockroachDB check is included in the [Datadog Agent][2] package, so you do not
need to install anything else on your server.

### Configuration

1. Edit the `cockroachdb.d/conf.yaml` file, in the `conf.d/` folder [at the root of your
   [Agent's configuration directory][3] to start collecting your cockroachdb performance data.
   See the [sample cockroachdb.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5]

### Validation

[Run the Agent's `status` subcommand][6] and look for `cockroachdb` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Service Checks

The CockroachDB check does not include any service checks.

### Events

The CockroachDB check does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][8].

## Further Reading
Additional helpful documentation, links, and articles:

* [Monitor CockroachDB performance metrics with Datadog][9]

[1]: https://www.cockroachlabs.com/product/cockroachdb
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files
[4]: https://github.com/DataDog/integrations-core/blob/master/cockroachdb/datadog_checks/cockroachdb/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/cockroachdb/metadata.csv
[8]: https://docs.datadoghq.com/help
[9]: https://www.datadoghq.com/blog/monitor-cockroachdb-performance-metrics-with-datadog
