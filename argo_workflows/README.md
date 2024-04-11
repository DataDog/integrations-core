# Agent Check: Argo Workflows

## Overview

This check monitors [Argo Workflows][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running in your Kubernetes environment. For more information about configuration in containerized environments, see the [Autodiscovery Integration Templates][3] for guidance.

### Installation

Starting from Agent release 7.53.0, the Argo Workflows check is included in the [Datadog Agent][2] package. No additional installation is needed in your environment.

This check uses [OpenMetrics][5] to collect metrics from the OpenMetrics endpoint.

### Configuration

The Argo Workflows Workflow Controller has [Prometheus-formatted metrics][11] available at `/metrics` on port `9090`. For the Agent to start collecting metrics, the Workflow Controller pod needs to be annotated. For more information about annotations, refer to the [Autodiscovery Integration Templates][3] for guidance. You can find additional configuration options by reviewing the [sample argo_workflows.d/conf.yaml][4].

The only parameter required for configuring the Argo Workflows check is:
- `openmetrics_endpoint`: This parameter should be set to the location where the Prometheus-formatted metrics are exposed. The default port is `9090`. In containerized environments, `%%host%%` should be used for [host autodetection][3].

```yaml
apiVersion: v1
kind: Pod
# (...)
metadata:
  name: '<POD_NAME>'
  annotations:
    ad.datadoghq.com/argo-workflows.checks: |
      {
        "argo_workflows": {
          "init_config": {},
          "instances": [
            {
              "openmetrics_endpoint": "http://%%host%%:9090/metrics",
            }
          ]
        }
      }
    # (...)
spec:
  containers:
    - name: 'argo-workflows'
# (...)
```

#### Log collection

_Available for Agent versions >6.0_

Argo Workflows logs can be collected from the different Argo Workflows pods through Kubernetes. Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][10].

See the [Autodiscovery Integration Templates][3] for guidance on applying the parameters below.

| Parameter      | Value                                                   |
| -------------- | ------------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "argo_workflows", "service": "<SERVICE_NAME>"}`  |

### Validation

[Run the Agent's status subcommand][6] and look for `argo_workflows` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Argo Workflows integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://argo-workflows.readthedocs.io/en/stable/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/argo_workflows/datadog_checks/argo_workflows/data/conf.yaml.example
[5]: https://docs.datadoghq.com/integrations/openmetrics/
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/argo_workflows/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/argo_workflows/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.datadoghq.com/agent/kubernetes/log/
[11]: https://argo-workflows.readthedocs.io/en/stable/metrics/
