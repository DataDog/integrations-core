# CoreDNS Integration

## Overview

Get metrics from CoreDNS in real time to visualize and monitor DNS failures and cache hits/misses.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][7] for guidance on applying these instructions.

### Installation

The CoreDNS check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

### Configuration

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][7] for guidance on applying the parameters below.

#### Metric Collection

| Parameter            | Value                                                                            |
| -------------------- | -------------------------------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `coredns`                                                                        |
| `<INIT_CONFIG>`      | blank or `{}`                                                                    |
| `<INSTANCE_CONFIG>`  | `{"prometheus_url":"http://%%host%%:9153/metrics", "tags":["dns-pod:%%host%%"]}` |

**Note:**

- The `dns-pod` tag keeps track of the target DNS pod IP. The other tags are related to the dd-agent that is polling the information using the service discovery.
- The service discovery annotations need to be done on the pod. In case of a deployment, add the annotations to the metadata of the template's specifications. Do not add it at the outer specification level.

##### Log collection

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes log collection documentation][9].

| Parameter      | Value                                     |
|----------------|-------------------------------------------|
| `<LOG_CONFIG>` | `{"source": "coredns", "service": "<SERVICE_NAME>"}` |

### Validation

[Run the Agent's `status` subcommand][4] and look for `coredns` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

### Events

The CoreDNS check does not include any events.

### Service Checks

`coredns.prometheus.health`:

Returns `CRITICAL` if the Agent cannot reach the metrics endpoints.

## Troubleshooting

Need help? Contact [Datadog support][6].

## Development

See the [main documentation][2]
for more details about how to test and develop Agent based integrations.

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/developers/
[3]: https://github.com/DataDog/integrations-core/blob/master/coredns/datadog_checks/coredns/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://github.com/DataDog/integrations-core/blob/master/coredns/metadata.csv
[6]: http://docs.datadoghq.com/help
[7]: https://docs.datadoghq.com/agent/kubernetes/integrations/
