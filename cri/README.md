# Agent Check: CRI

## Overview

This check monitors a Container Runtime Interface

## Setup

### Installation

CRI is a core agent 6 check and thus need to be configured in both in `datadog.yaml` and with `cri.d/conf.yaml`.

In `datadog.yaml` you will need to configure your `cri_socket_path` for the agent to query your current CRI (you can also configure default timeouts) and in `cri.d/conf.yaml` you can configure the check instance settings such as `collect_disk` if your CRI (such as `containerd`) reports disk usage metrics.

Note that if you're using the agent in a container, setting `DD_CRI_SOCKET_PATH` environment variable will automatically enable the `CRI` check with the default configuration.

### Configuration

1. Edit the `cri.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your crio performance data.
   See the [sample cri.d/conf.yaml][1] for all available configuration options.

2. [Restart the Agent][2]

### Validation

[Run the Agent's `status` subcommand][3] and look for `cri` under the Checks section.

## Data Collected

### Metrics

CRI collect metrics about the resource usage of your containers running through the CRI.

CPU and memory metrics are collected out of the box and you can additionally collect some disk metrics
if they are supported by your CRI (CRI-O doesn't support them for now)

See [metadata.csv][4] for a list of metrics provided by this integration.

### Service Checks

CRI does not include service checks.

### Events

CRI does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][5].

[1]: https://github.com/DataDog/datadog-agent/blob/master/cmd/agent/dist/conf.d/cri.d/conf.yaml.example
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[4]: https://github.com/DataDog/integrations-core/blob/master/cri/metadata.csv
[5]: https://docs.datadoghq.com/help
