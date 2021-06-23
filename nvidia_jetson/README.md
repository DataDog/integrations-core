# Agent Check: Nvidia Jetson

## Overview

This check monitors an [Nvidia Jetson][2] board.
It reports the metrics collected from `tegrastats`.

## Setup

### Installation

The Nvidia Jetson check is included in the [Datadog Agent][3] package.
No additional installation is needed on your server.

### Configuration

1. Create a `jetson.d/conf.yaml` file in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your Jetson performance data.
   See the [sample jetson.d/conf.yaml.example][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `jetson` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this check.

Some metrics are reported only if `use_sudo` is set to true:
- `nvidia.jetson.iram.used`
- `nvidia.jetson.iram.total`
- `nvidia.jetson.iram.lfb`
- `nvidia.jetson.emc.freq`
- `nvidia.jetson.gpu.freq`
- `nvidia.jetson.cpu.freq`

### Service Checks

Nvidia Jetson does not include any service checks.

### Events

Nvidia Jetson does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: https://developer.nvidia.com/embedded-computing
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://github.com/DataDog/datadog-agent/blob/master/cmd/agent/dist/conf.d/jetson.d/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/nvidia_jetson/metadata.csv