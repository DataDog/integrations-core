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

   This check has a limit of 350 metrics per instance. The number of returned metrics is indicated in the info page.
   You can specify the metrics you are interested in by editing the configuration below. 
   To learn how to customize the metrics to collect visit the [JMX Checks documentation][3] for more detailed instructions.
   If you need to monitor more metrics, please send us an email at support@datadoghq.com

2. [Restart the Agent][4]

### Validation

[Run the Agent's `status` subcommand][5] and look for `{check_name}` under the Checks section.

## Data Collected

### Metrics

{check_name_cap} does not include any metrics.

### Service Checks

{check_name_cap} does not include any service checks.

### Events

{check_name_cap} does not include any events.

## Troubleshooting

Need help? Contact [Datadog Support][6].


[1]: **LINK_TO_INTEGERATION_SITE**
[2]: https://github.com/DataDog/integrations-core/blob/master/{check_name}/datadog_checks/{check_name}/data/conf.yaml.example
[3]: https://docs.datadoghq.com/integrations/java/
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[6]: https://docs.datadoghq.com/help/
