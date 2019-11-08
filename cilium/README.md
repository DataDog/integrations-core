# Agent Check: Cilium

## Overview

This check monitors [Cilium][1] through the Datadog Agent. The integration can either collect metrics from the `cilium-agent` or `cilium-operator`.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The Cilium check is included in the [Datadog Agent][2] package, but it requires additional setup steps to export Prometheus metrics.

1. In order to collect `cilium-agent` metrics, you must enable Prometheus metrics. There are two ways to do this. Either:
    * Deploy Cilium with the `global.prometheus.enabled=true` Helm value set, or:
    * Add `--prometheus-serve-addr=:9090` to the `args` section of the Cilium DaemonSet config.
        ```
        [...]
            spec:
                containers:
                - args:
                    - --prometheus-serve-addr=:9090

        ```
2. In order to collect `cilium-operator` metrics, the Prometheus metrics must be enabled by adding `- --enable-metrics` to the args section of the Cilium deployment config.
    * The operator metrics are enabled if Cilium is deployed with the `global.prometheus.enabled=true` Helm value set.


### Configuration

1. Edit the `cilium.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your cilium performance data. See the [sample cilium.d/conf.yaml][3] for all available configuration options.
    * To collect `cilium-agent` metrics, enable the `agent_url` option.
    * To collect `cilium-operator` metrics, enable the `operator_url` option.

2. [Restart the Agent][4].

### Validation

[Run the Agent's status subcommand][5] and look for `cilium` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of all metrics provided by this integration.

### Service Checks

`cilium.prometheus.health`: Returns `CRITICAL` if the Agent cannot reach the metrics endpoints, `OK` otherwise.

### Events

Cilium does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: https://cilium.io/
[2]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[3]: https://github.com/DataDog/integrations-core/blob/master/cilium/datadog_checks/cilium/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/cilium/metadata.csv
[7]: https://docs.datadoghq.com/help
