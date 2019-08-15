# Windows Performance Counters Integration

## Overview

Get metrics from Windows performance counters in real time to:

* Visualize and monitor windows performance counters through the pdh api

## Setup
### Installation

The PDH check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your servers.

### Configuration

Edit the `pdh_check.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3] to collect Windows performance data. See the [sample pdh_check.d/conf.yaml][4] for all available configuration options.

### Validation

[Run the Agent's `status` subcommand][5] and look for `pdh_check` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][6] for a list of metrics provided by this integration.

### Events
The PDH check does not include any events.

### Service Checks
The PDH check does not include any service checks.


[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/pdh_check/datadog_checks/pdh_check/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/pdh_check/metadata.csv
