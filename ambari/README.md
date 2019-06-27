# Agent Check: Ambari

## Overview

This check monitors [Ambari][1] through the Datadog Agent.

![Ambari Dashboard][9]

## Setup

### Installation

The Ambari check is included in the [Datadog Agent][6] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `ambari.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to
start collecting your Ambari performance data. See the [sample ambari.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3].

### Validation

[Run the Agent's status subcommand][4] and look for `ambari` under the Checks section.


### Metrics

This integration collects for every host in every cluster the following system metrics:

* boottime
* cpu
* disk
* memory
* load
* network
* process

If service metrics collection is enabled with `collect_service_metrics` this integration will collect for each
whitelisted service component the metrics with headers in the white list.
See [metadata.csv][7] for a list of all metrics provided by this integration.

### Service Checks

- `ambari.can_connect` - Returns `OK` if the cluster is reachable, `CRITICAL` otherwise.
- `ambari.state` - Returns `OK` if the service is installed or running, `WARNING` if the service is stopping or uninstalling,
  or `CRITICAL` if the service is uninstalled or stopped. For a complete enumeration, see [this file][8].

### Events

Ambari does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][5].

[1]: https://ambari.apache.org/
[2]: https://github.com/DataDog/integrations-core/blob/master/ambari/datadog_checks/ambari/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[5]: https://docs.datadoghq.com/help
[6]: https://docs.datadoghq.com/agent/
[7]: https://github.com/DataDog/integrations-core/blob/master/ambari/datadog_checks/ambari/data/conf.yaml.example
[8]: https://github.com/DataDog/integrations-core/blob/master/ambari/datadog_checks/ambari/common.py
[9]: https://raw.githubusercontent.com/DataDog/integrations-core/master/ambari/assets/images/base_dashboard.png
