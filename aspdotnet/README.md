# ASP.NET Integration

## Overview

Get metrics from ASP.NET service in real time to:

* Visualize and monitor ASP.NET states
* Be notified about ASP.NET failovers and events.

## Setup
### Installation

The ASP.NET check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

### Configuration

1. Edit the `aspdotnet.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][6] to start collecting your ASP.NET performance data.

    See the [sample aspdotnet.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][5]

### Validation

[Run the Agent's `status` subcommand][2] and look for `aspdotnet` under the Checks section.

## Data Collected
### Metrics
The ASP.NET check does not include any metrics at this time.

### Events
All ASP.NET events and failovers are sent to your [Datadog event stream][4]

### Service Checks
The ASP.NET check does not include any service checks at this time.

## Troubleshooting
Need help? Contact [Datadog Support][5].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[3]: https://github.com/DataDog/integrations-core/blob/master/aspdotnet/datadog_checks/aspdotnet/data/conf.yaml.example
[4]: https://app.datadoghq.com/event/stream
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[6]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
