# Agent Check: {check_name_cap}

## Overview

This check monitors [{check_name_cap}][1].

## Setup

### Installation

{install_info}

### Configuration

1. Edit the `{check_name}.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your {check_name} performance data.
   See the [sample {check_name}.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3]

### Validation

[Run the Agent's `status` subcommand][4] and look for `{check_name}` under the Checks section.

## Data Collected

### Metrics

{check_name_cap} does not include any metrics.

### Service Checks

{check_name_cap} does not include any service checks.

### Events

{check_name_cap} does not include any events.

## Troubleshooting

Need help? Contact [Datadog Support][5].

[1]: **LINK_TO_INTEGERATION_SITE**
[2]: https://github.com/DataDog/integrations-core/blob/master/{check_name}/datadog_checks/{check_name}/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://docs.datadoghq.com/help/
