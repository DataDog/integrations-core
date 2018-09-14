# Agent Check: CRI-O

## Overview

This check monitors [Crio][1].

## Setup

### Installation

The integration relies on the `--enable-metrics` option of CRI-O that is disabled by default, when enabled metrics will be exposed at `127.0.0.1:9090/metrics`.

### Configuration

1. Edit the `crio.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your crio performance data.
   See the [sample crio.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3]

### Validation

[Run the Agent's `status` subcommand][4] and look for `crio` under the Checks section.

## Data Collected

### Metrics

CRI-O collect metrics about the count and latency of operations that are done by the runtime.
We're also collecting

### Service Checks

CRI-O includes a service check about the reachability of the metrics endpoint.

### Events

Crio does not include any events.

## Troubleshooting

Need help? Contact [Datadog Support][6].

[1]: **LINK_TO_INTEGERATION_SITE**
[3]: https://github.com/DataDog/integrations-core/blob/master/crio/datadog_checks/crio/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[6]: https://docs.datadoghq.com/help/
