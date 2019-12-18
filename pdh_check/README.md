# Windows Performance Counters Integration

## Overview

Get metrics from Windows performance counters in real time to:

* Visualize and monitor Windows performance counters through the PDH API.

## Setup
### Installation

The PDH check is included in the [Datadog Agent][2] package. No additional installation is needed.

### Configuration

1. Edit the `pdh_check.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3] to collect Windows performance data. See the [sample pdh_check.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][9].

### Validation

Run the [Agent's status subcommand][5] and look for `pdh_check` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][6] for a list of metrics provided by this integration.

#### Custom metrics

The PDH check can potentially emit [custom metrics][7], which may impact your [billing][8].

### Events

The PDH check does not include any events.

### Service Checks

The PDH check does not include any service checks.


[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/pdh_check/datadog_checks/pdh_check/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/pdh_check/metadata.csv
[7]: https://docs.datadoghq.com/developers/metrics/custom_metrics
[8]: https://docs.datadoghq.com/account_management/billing/custom_metrics
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#restart-the-agent
