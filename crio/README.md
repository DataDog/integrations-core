# Agent Check: CRI-O

## Overview

This check monitors [CRI-O][1].

## Setup

### Installation

The integration relies on the `--enable-metrics` option of CRI-O that is disabled by default, when enabled metrics are exposed at `127.0.0.1:9090/metrics`.

### Configuration

1. Edit the `crio.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your CRI-O performance data. See the [sample crio.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3].

### Validation

[Run the Agent's status subcommand][4] and look for `crio` under the Checks section.

## Data Collected

CRI-O collects metrics about the count and latency of operations that are done by the runtime.
The Datadog-CRI-O integration collects CPU and memory usage of the CRI-O golang binary itself.

### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

### Service Checks

**crio.prometheus.health**:<br>
Returns `CRITICAL` if the Agent cannot reach the metrics endpoints.

### Events

CRI-O does not include any events.

### Service Checks

See [service_checks.json][6] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][7].


[1]: http://cri-o.io
[2]: https://github.com/DataDog/integrations-core/blob/master/crio/datadog_checks/crio/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#restart-the-agent
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-information
[5]: https://github.com/DataDog/integrations-core/blob/master/crio/metadata.csv
[6]: https://github.com/DataDog/integrations-core/blob/master/crio/assets/service_checks.json
[7]: https://docs.datadoghq.com/help/
