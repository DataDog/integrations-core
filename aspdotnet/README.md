# ASP.NET Integration

## Overview

Get metrics from ASP.NET in real time to:

- Visualize and monitor ASP.NET states.
- Be notified about ASP.NET failovers and events.

## Setup

### Installation

The ASP.NET check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

### Configuration

1. Edit the `aspdotnet.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2] to start collecting your ASP.NET performance data. See the [sample aspdotnet.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4]

**Note**: Versions 1.9.0 or later of this check use a new implementation for metric collection, which requires Python 3. For hosts that are unable to use Python 3, or if you would like to use a legacy version of this check, refer to the following [config][9].

#### Log collection

ASP.NET uses IIS logging. Follow the [setup instructions for IIS][5] in order to view logs related to ASP.NET requests and failures.

Unhandled 500 level exceptions and events related to your ASP.NET application can be viewed with the Windows Application EventLog.

### Validation

[Run the Agent's `status` subcommand][6] and look for `aspdotnet` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this check.

### Events

The ASP.NET check does not include any events.

### Service Checks

The ASP.NET check does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://app.datadoghq.com/account/settings/agent/latest
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/aspdotnet/datadog_checks/aspdotnet/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/integrations/iis/?tab=host#setup
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/aspdotnet/metadata.csv
[8]: https://docs.datadoghq.com/help/
[9]: https://github.com/DataDog/integrations-core/blob/7.33.x/aspdotnet/datadog_checks/aspdotnet/data/conf.yaml.example
