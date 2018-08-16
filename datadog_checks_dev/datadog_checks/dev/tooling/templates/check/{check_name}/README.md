# Agent Check: {check_name_cap}
## Overview

This check monitors [{check_name_cap}][1].

## Setup

### Installation

The {check_name_cap} check is included in the [Datadog Agent][2] package, so you don't
need to install anything else on your server.

### Configuration

1. Edit the `{check_name}.d/conf.yaml` file, in the `conf.d/` folder at the root of your
  Agent's configuration directory to start collecting your {check_name} performance data.
  See the [sample {check_name}.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4]

### Validation

[Run the Agent's `status` subcommand][5] and look for `{check_name}` under the Checks section.

## Data Collected
### Metrics

The {check_name_cap} check does not include any metrics at this time.

### Service Checks

The {check_name_cap} check does not include any service checks at this time.

### Events

The {check_name_cap} check does not include any events at this time.

## Troubleshooting

Need help? Contact [Datadog Support][6].

[1]: link to integration's site
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://github.com/DataDog/integrations-core/blob/master/{check_name}/datadog_checks/{check_name}/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[6]: https://docs.datadoghq.com/help/
