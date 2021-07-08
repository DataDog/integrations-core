# Agent Check: {integration_name}

## Overview

This check monitors [{integration_name}][1].

## Setup

### Installation

{install_info}

### Configuration

1. Edit the `{check_name}.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your {check_name} performance data.
   See the [sample {check_name}.d/conf.yaml][2] for all available configuration options.

   This check has a limit of 350 metrics per instance. The number of returned metrics is indicated in the info page.
   You can specify the metrics you are interested in by editing the configuration below.
   To learn how to customize the metrics to collect visit the [JMX Checks documentation][3] for more detailed instructions.
   If you need to monitor more metrics, contact [Datadog support][4].

2. [Restart the Agent][5]

### Validation

[Run the Agent's `status` subcommand][6] and look for `{check_name}` under the Checks section.

## Data Collected

### Metrics

{integration_name} does not include any metrics.

### Events

The {integration_name} integration does not include any events.

### Service Checks

The {integration_name} integration does not include any service checks.

See [service_checks.json][7] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][4].


[1]: **LINK_TO_INTEGERATION_SITE**
[2]: https://github.com/DataDog/integrations-{repo_choice}/blob/master/{check_name}/datadog_checks/{check_name}/data/conf.yaml.example
[3]: https://docs.datadoghq.com/integrations/java/
[4]: https://docs.datadoghq.com/help/
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/{check_name}/assets/service_checks.json
