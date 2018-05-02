# Dotnetclr Integration

## Overview

Get metrics from dotnetclr service in real time to:

* Visualize and monitor dotnetclr states
* Be notified about dotnetclr failovers and events.

## Installation

The Dotnetclr check is packaged with the Agent, so simply [install the Agent][1] on your servers.

## Configuration

Edit the `dotnetclr.yaml` file to point to your server and port, set the masters to monitor

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
