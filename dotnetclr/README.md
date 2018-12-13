# Dotnetclr Integration

## Overview

Get metrics from Dotnetclr service in real time to:

* Visualize and monitor Dotnetclr states
* Be notified about Dotnetclr failovers and events.

## Installation

The Dotnetclr check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

## Configuration

1. Edit the `dotnetclr.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2] to start collecting your Dotnetclr performance data.
    See the [sample dotnetclr.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4]

## Validation

[Run the Agent's `status` subcommand][3] and look for `dotnetclr` under the Checks section.

## Troubleshooting
Need help? Contact [Datadog Support][5].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[5]: https://docs.datadoghq.com/help
