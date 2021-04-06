# ASP.NET Integration

## Overview

Get metrics from ASP.NET in real time to:

- Visualize and monitor ASP.NET states.
- Be notified about ASP.NET failovers and events.

## Setup

### Installation

The ASP.NET check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your servers.

### Configuration

1. Edit the `aspdotnet.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3] to start collecting your ASP.NET performance data. See the [sample aspdotnet.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5]

#### Log Collection
ASP.NET uses IIS logging. Follow the [setup instructions for IIS][9] in order to view logs related to ASP.NET requests and failures. 

Unhandled 500 level exceptions and events related to your ASP.NET application can be viewed via the Windows Application EventLog. 

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

[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/aspdotnet/datadog_checks/aspdotnet/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/aspdotnet/metadata.csv
[8]: https://docs.datadoghq.com/help/
[9]: https://docs.datadoghq.com/integrations/iis/?tab=host#setup
