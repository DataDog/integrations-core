# Windows Performance Counters Integration

## Overview

Get metrics from Windows performance counters in real time to:

* Visualize and monitor windows performance counters through the pdh api

## Setup
### Installation

The PDH check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

### Configuration

Edit the `pdh_check.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][5] to collect Windows performance data. See the [sample pdh_check.d/conf.yaml][2] for all available configuration options.

### Validation

[Run the Agent's `status` subcommand][3] and look for `pdh_check` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][4] for a list of metrics provided by this integration.

### Events
The PDH check does not include any events at this time.

### Service Checks
The PDH check does not include any service checks at this time.


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/pdh_check/datadog_checks/pdh_check/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[4]: https://github.com/DataDog/integrations-core/blob/master/pdh_check/metadata.csv
[5]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
