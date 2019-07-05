# Dotnetclr Integration

## Overview

Get metrics from Dotnetclr service in real time to:

* Visualize and monitor Dotnetclr states
* Be notified about Dotnetclr failovers and events.

## Setup

Find below instructions to install and configure the check when running the Agent on a host. See the [Autodiscovery Integration Templates documentation][1] to learn how to apply those instructions to a containerized environment.

### Installation

The Dotnetclr check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your servers.

### Configuration

1. Edit the `dotnetclr.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3] to start collecting your Dotnetclr performance data.
    See the [sample dotnetclr.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5]

## Validation

[Run the Agent's `status` subcommand][4] and look for `dotnetclr` under the Checks section.

## Troubleshooting
Need help? Contact [Datadog support][6].

[1]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6#agent-configuration-directory
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/help
