# Agent Check: Openstack_controller

## Overview

DISCLAIMER: This integration is in beta and should not be used.

This check monitors [Openstack_controller][1].

## Setup

### Installation

The Openstack_controller check is included in the [Datadog Agent][2] package, so you do not
need to install anything else on your server.

### Configuration

1. Edit the `openstack_controller.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your openstack_controller performance data.
   See the [sample openstack_controller.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3]

### Validation

[Run the Agent's `status` subcommand][4] and look for `openstack_controller` under the Checks section.

## Data Collected

### Metrics

Openstack_controller does not include any metrics.

### Service Checks

Openstack_controller does not include any service checks.

### Events

Openstack_controller does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][5].

[1]: **LINK_TO_INTEGERATION_SITE**
[2]: https://github.com/DataDog/integrations-core/blob/master/openstack_controller/datadog_checks/openstack_controller/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://docs.datadoghq.com/help/
