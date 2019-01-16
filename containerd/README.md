# Agent Check: Containerd

## Overview

This check monitors the Container Runtime Containerd

## Setup

### Installation

Containerd is a core agent 6 check and thus needs to be configured in both in `datadog.yaml` and with `containerd.d/conf.yaml`.

In `datadog.yaml` configure your `cri_socket_path` for the agent to query Containerd and in `containerd.d/conf.yaml` configure the check instance settings such as `filters` for the events.

**Note** if you are using the agent in a container, setting `DD_CRI_SOCKET_PATH` environment variable automatically enables the `Containerd` check with the default configuration.

### Configuration

1. Edit the `containerd.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your Containerd performance data.
   See the [sample containerd.d/conf.yaml][1] for all available configuration options.

2. [Restart the Agent][3]

### Validation

[Run the Agent's `status` subcommand][2] and look for `containerd` under the Checks section.

## Data Collected

### Metrics

Containerd collects metrics about the resource usage of your containers.

CPU, memory, block I/O or huge page table metrics are collected out of the box and you can additionally collect some disk metrics.

See [metadata.csv][4] for a list of metrics provided by this integration.

### Service Checks

Containerd includes a service check `containerd.health` to notify on the health of the connection to the Containerd Socket.

### Events

The Containerd check can collect events, you can use `filters` to select the event kinds you want to get. Refer to the [sample containerd.d/conf.yaml][1] to have more details.

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: https://github.com/DataDog/datadog-agent/blob/master/cmd/agent/dist/conf.d/containerd.d/conf.yaml.example
[2]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[3]: https://docs.datadoghq.com/help/
[4]: https://github.com/DataDog/integrations-core/blob/master/cri/metadata.csv
