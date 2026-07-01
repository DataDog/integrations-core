# Agent Check: GPU

## Overview

This check monitors GPU devices and their utilization through the Datadog Agent. This is part of the [Datadog GPU Monitoring feature][1].

Supported vendors: NVIDIA.

- Track utilization of GPU devices and retrieve performance and health metrics.
- Monitor processes that are using GPU devices and their performance.

## Setup

Setup instructions for the GPU Monitoring feature are available in the [GPU Monitoring setup documentation][2].


### Validation

[Run the Agent's status subcommand][3] and look for `gpu` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][4] for a list of metrics provided by this check.

### Events

The GPU check does not include any events.

### Service Checks

The GPU check does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][5].

[1]: https://www.datadoghq.com/product/gpu-monitoring/
[2]: https://docs.datadoghq.com/gpu_monitoring/setup/
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[4]: https://github.com/DataDog/integrations-core/blob/master/gpu/metadata.csv
[5]: https://docs.datadoghq.com/help/
