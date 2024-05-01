# Agent Check: fluxcd

## Overview

This check monitors [Flux][1] through the Datadog Agent. Flux is a set of continuous and progressive delivery solutions for Kubernetes that is open and extensible.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

Starting from Agent release 7.51.0, the Fluxcd check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

For older versions of the Agent, [use these steps to install][10] the integration.


### Configuration

This integration supports collecting metrics and logs from the following Flux services:

- `helm-controller`
- `kustomize-controller`
- `notification-controller`
- `source-controller`

You can pick and choose which services you monitor depending on your needs.

#### Metric collection

This is an example configuration with Kubernetes annotations on your Flux pods. See the [sample configuration file][4] for all available configuration options.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: '<POD_NAME>'
  annotations:
    ad.datadoghq.com/fluxcd.checks: |-
      {
        "fluxcd": {
          "instances": [
            {
              "openmetrics_endpoint": "http://%%host%%:8080/metrics"
            }
          ]
        }
      }
    # (...)
spec:
  containers:
    - name: 'fluxcd'
# (...)
```

#### Log collection

_Available for Agent versions >6.0_

Flux logs can be collected from the different Flux pods through Kubernetes. Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][12].

See the [Autodiscovery Integration Templates][3] for guidance on applying the parameters below.

| Parameter      | Value                                                   |
| -------------- | ------------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "fluxcd", "service": "<SERVICE_NAME>"}`  |

### Validation

[Run the Agent's status subcommand][6] and look for `fluxcd` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The fluxcd integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].

## Further Reading

Additional helpful documentation, links, and articles:

- [Monitoring your container-native technologies][11]


[1]: https://fluxcd.io/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/7.51.x/fluxcd/datadog_checks/fluxcd/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/fluxcd/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/fluxcd/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.datadoghq.com/agent/guide/use-community-integrations/?tab=agentv721v621#installation
[11]: https://www.datadoghq.com/blog/container-native-integrations/#cicd-with-flux
[12]: https://docs.datadoghq.com/agent/kubernetes/log/
