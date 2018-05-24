# Dotnetclr Integration

## Overview

Get metrics from dotnetclr service in real time to:

* Visualize and monitor dotnetclr states
* Be notified about dotnetclr failovers and events.

## Installation

The Dotnetclr check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

## Configuration

1. Edit the `dotnetclr.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's directory to start collecting your dotnetclr performance data. 
    See the [sample dotnetclr.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][5]

## Validation

[Run the Agent's `status` subcommand][2] and look for `dotnetclr` under the Checks section.

## Troubleshooting
Need help? Contact [Datadog Support][3].

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog][4]


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[3]: http://docs.datadoghq.com/help/
[4]: https://www.datadoghq.com/blog/
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
