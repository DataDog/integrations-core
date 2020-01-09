# Agent Check: Cilium

## Overview

This check monitors [Cilium][1] through the Datadog Agent. The integration can either collect metrics from the `cilium-agent` or `cilium-operator`.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The Cilium check is included in the [Datadog Agent][3] package, but it requires additional setup steps to expose Prometheus metrics.

1. In order to enable Prometheus metrics in both the `cilium-agent` and `cilium-operator`, deploy Cilium with the `global.prometheus.enabled=true` Helm value set, or:

2. Separately enable Prometheus metrics in the `cilium-agent`:
    * Add `--prometheus-serve-addr=:9090` to the `args` section of the Cilium DaemonSet config.
        ```
        [...]
            spec:
                containers:
                - args:
                    - --prometheus-serve-addr=:9090
        ```
    or in the `cilium-operator`:
    * Add `--enable-metrics` to the `args` section of the Cilium deployment config.
        ```
        [...]
            spec:
                containers:
                - args:
                    - --enable-metrics
        ```

To collect the cluster-wide `cilium-operator` metrics, see the [Cluster Agent][9].

### Configuration

1. Edit the `cilium.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Cilium performance data. See the [sample cilium.d/conf.yaml][4] for all available configuration options.
    * To collect `cilium-agent` metrics, enable the `agent_endpoint` option.
    * To collect `cilium-operator` metrics, enable the `operator_endpoint` option.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `cilium` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of all metrics provided by this integration.

### Service Checks

`cilium.prometheus.health`: Returns `CRITICAL` if the Agent cannot reach the metrics endpoints, `OK` otherwise.

### Events

Cilium does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://cilium.io
[2]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[3]: https://docs.datadoghq.com/agent
[4]: https://github.com/DataDog/integrations-core/blob/master/cilium/datadog_checks/cilium/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/cilium/metadata.csv
[8]: https://docs.datadoghq.com/help
[9]: https://docs.datadoghq.com/agent/cluster_agent
