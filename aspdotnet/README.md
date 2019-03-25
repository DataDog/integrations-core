# ASP.NET Integration

## Overview

Get metrics from ASP.NET service in real time to:

* Visualize and monitor ASP.NET states
* Be notified about ASP.NET failovers and events.

## Setup
### Installation

The ASP.NET check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

### Configuration

1. Edit the `aspdotnet.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2] to start collecting your ASP.NET performance data.

    See the [sample aspdotnet.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4]

### Validation

[Run the Agent's `status` subcommand][5] and look for `aspdotnet` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Events
The ASP.NET check does not include any events.

### Service Checks
The ASP.NET check does not include any service checks.

## Troubleshooting
Need help? Contact [Datadog support][7].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/aspdotnet/datadog_checks/aspdotnet/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/aspdotnet/metadata.csv
[7]: https://docs.datadoghq.com/help/
