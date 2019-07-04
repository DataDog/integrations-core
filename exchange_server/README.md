# Microsoft Exchange Server Integration

## Overview

Get metrics from Microsoft Exchange Server

* Visualize and monitor Exchange server performance

## Setup

Find below instructions to install and configure the check when running the Agent on a host. See the [Autodiscovery Integration Templates documentation](https://docs.datadoghq.com/agent/autodiscovery/integrations/) to learn how to transpose those instructions in a containerized environment.

### Installation

The Exchange check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

### Configuration

1. Edit the `exchange_server.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][2] to start collecting your Exchange Server performance data.

  ```yaml
  init_config:
  instances:
    - host: .
  ```

2. [Restart the Agent][3]

### Validation

[Run the Agent's `status` subcommand][4] and look for `exchange_server` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][5] for a list of metrics provided by this integration.

### Events
The Exchange server check does not include any events.

### Service Checks
The Exchange server check does not include any service checks.


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6#agent-configuration-directory
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/exchange_server/metadata.csv
