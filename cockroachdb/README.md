# Agent Check: CockroachDB

## Overview

This check monitors [CockroachDB][1].

## Setup

### Installation

The CockroachDB check is included in the [Datadog Agent][2] package, so you do not
need to install anything else on your server.

### Configuration

1. Edit the `cockroachdb.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your cockroachdb performance data.
   See the [sample cockroachdb.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4]

### Validation

[Run the Agent's `status` subcommand][5] and look for `cockroachdb` under the Checks section.

## Data Collected

### Metrics

CockroachDB does not include any metrics.

### Service Checks

CockroachDB does not include any service checks.

### Events

CockroachDB does not include any events.

## Troubleshooting

Need help? Contact [Datadog Support][6].

[1]: **LINK_TO_INTEGERATION_SITE**
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://github.com/DataDog/integrations-core/blob/master/cockroachdb/datadog_checks/cockroachdb/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[6]: https://docs.datadoghq.com/help/
