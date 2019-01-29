# Windows Performance Counters Integration

## Overview

Get metrics from Windows performance counters in real time to:

* Visualize and monitor windows performance counters through the pdh api

## Setup
### Installation

The PDH check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

### Configuration

Edit the `pdh_check.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2] to collect Windows performance data. See the [sample pdh_check.d/conf.yaml][3] for all available configuration options.

### Validation

[Run the Agent's `status` subcommand][4] and look for `pdh_check` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][5] for a list of metrics provided by this integration.

### Events
The PDH check does not include any events.

### Service Checks
The PDH check does not include any service checks.


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/pdh_check/datadog_checks/pdh_check/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/pdh_check/metadata.csv
