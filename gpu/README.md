# Agent Check: GPU

## Overview

This check monitors GPU devices and their utilization through the Datadog Agent. This is part of the [Datadog GPU Monitoring feature][1]

Supported vendors: NVIDIA.

- Track utilization of GPU devices and retrieve performance and health metrics.
- Monitor processes that are using GPU devices and their performance.


## Setup

Setup instructions for the GPU Monitoring feature are available in our [documentation][2].

### Validation

[Run the Agent's status subcommand][5] and look for `gpu` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Events

The GPU check does not include any events.

### Service Checks

The GPU check does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://www.datadoghq.com/product/gpu-monitoring/
[2]: https://docs.datadoghq.com/gpu_monitoring/setup/
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/gpu/metadata.csv
[8]: https://docs.datadoghq.com/help/
