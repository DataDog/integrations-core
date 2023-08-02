# Agent Check: Systemd

## Overview

This check monitors [Systemd][1] and the units it manages through the Datadog Agent.

- Track the state and health of your Systemd
- Monitor the units, services, sockets managed by Systemd

## Setup

### Installation

The Systemd check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

1. Edit the `systemd.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your systemd performance data.
   See the [sample systemd.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, mount the `/run/systemd/` folder, which contains the socket `/run/systemd/private` needed to retrieve the Systemd data, for example:

```bash
docker run -d -v /var/run/docker.sock:/var/run/docker.sock:ro \
              -v /proc/:/host/proc/:ro \
              -v /sys/fs/cgroup/:/host/sys/fs/cgroup/:ro \
              -v /run/systemd/:/host/run/systemd/:ro \
              -e DD_API_KEY=<YOUR_API_KEY> \
              datadog/agent:latest
```

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][5] and look for `systemd` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

Some metrics are reported only if the respective configuration are enabled:

- `systemd.service.cpu_time_consumed` requires Systemd configuration `CPUAccounting` to be enabled
- `systemd.service.memory_usage` requires Systemd configuration `MemoryAccounting` to be enabled
- `systemd.service.task_count` requires Systemd configuration `TasksAccounting` to be enabled

Some metrics are only available from specific version of Systemd:

- `systemd.service.cpu_time_consumed` requires Systemd v220
- `systemd.service.restart_count` requires Systemd v235
- `systemd.socket.connection_refused_count` requires Systemd v239

### Events

The Systemd check does not include any events.

### Service Checks

See [service_checks.json][7] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][8].


[1]: https://www.freedesktop.org/wiki/Software/systemd/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://github.com/DataDog/datadog-agent/blob/master/cmd/agent/dist/conf.d/systemd.d/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/systemd/metadata.csv
[7]: https://github.com/DataDog/integrations-core/blob/master/systemd/assets/service_checks.json
[8]: https://docs.datadoghq.com/help/
