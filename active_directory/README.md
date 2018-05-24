# active_directory Integration

## Overview

Get metrics from Microsoft Active Directory to visualize and monitor its performances.

## Setup
### Installation

The Agent's Active directory check is included in the [Datadog Agent][4] package, so you don't need to install anything else on your servers.

### Configuration

1. Edit the `active_directory.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's directory to start collecting your Active Directory performance data.  

    See the [sample active_directory.d/conf.yaml][1] for all available configuration options.

2. [Restart the Agent][7]

### Validation

[Run the Agent's `info` subcommand][2] and look for `active_directory` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][3] for a list of metrics provided by this integration.

### Events
The active directory check does not include any event at this time.

### Service Checks
The active directory check does not include any service check at this time.

## Troubleshooting
Need help? Contact [Datadog Support][5].

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog][6]

[1]: https://github.com/DataDog/integrations-core/blob/master/active_directory/conf.yaml.example
[2]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[3]: https://github.com/DataDog/integrations-core/blob/master/active_directory/metadata.csv
[4]: https://app.datadoghq.com/account/settings#agent
[5]: http://docs.datadoghq.com/help/
[6]: https://www.datadoghq.com/blog/
[7]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent