# Agent Check: Ambari

## Overview

This check monitors [Ambari][1] through the Datadog Agent.

## Setup

### Installation

The Ambari check is included in the [Datadog Agent][6] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `ambari.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to
start collecting your Ambari performance data. See the [sample ambari.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3].

#### Log Collection

To enable collecting logs in the Datadog Agent, update `logs_enabled` in `datadog.yaml`:
```
    logs_enabled: true
```

Next, edit `ambari.d/conf.yaml` by uncommenting the `logs` lines at the bottom. Update the logs `path` with the correct path to your Ambari log files.

```yaml
 logs:
   - type: file
     path: /var/log/ambari-server/ambari-alerts.log
     source: ambari
     service: ambari
     log_processing_rules:
        - type: multi_line
          name: new_log_start_with_date
          pattern: \d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01])  # 2019-04-22 15:47:00,999
...
```

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