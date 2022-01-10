# Agent Check: {integration_name}

## Overview

This check monitors [{integration_name}][1].

## Setup

### Installation

{install_info}

### Configuration

1. Edit the `{check_name}.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your {check_name} performance data.
   See the [sample {check_name}.d/conf.yaml][3] for all available configuration options.

   This check has a limit of 350 metrics per instance. The number of returned metrics is indicated when running the Datadog Agent [status command][4].
   You can specify the metrics you are interested in by editing the [configuration][3].
   To learn how to customize the metrics to collect visit the [JMX Checks documentation][5] for more detailed instructions.
   If you need to monitor more metrics, contact [Datadog support][6].

2. [Restart the Agent][7]

### Validation

[Run the Agent's `status` subcommand][4] and look for `{check_name}` under the Checks section.

## Data Collected

### Metrics

{integration_name} does not include any metrics.

### Events

The {integration_name} integration does not include any events.

### Service Checks

The {integration_name} integration does not include any service checks.

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][6].


{integration_links}