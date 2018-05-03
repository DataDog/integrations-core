# Wmi_check Integration

## Overview

Get metrics from Windows performance counters in real time to:

* Visualize and monitor windows performance counters

## Setup
### Installation

The PDH check is packaged with the Agent, so simply [install the Agent][1] on your servers.

### Configuration

Edit the `pdh_check.yaml` file to collect Windows performance data. See the [sample pdh_check.yaml][2] for all available configuration options.

### Validation

[Run the Agent's `status` subcommand][3] and look for `pdh_check` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][4] for a list of metrics provided by this integration.

### Events
The PDH check does not include any event at this time.

### Service Checks
The PDH check does not include any service check at this time.


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/pdh_check/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[4]: https://github.com/DataDog/integrations-core/blob/master/pdh_check/metadata.csv
