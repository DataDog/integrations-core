# Agent Check: Argo Rollouts

## Overview

This check monitors [Argo Rollouts][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running in your Kubernetes environment. For more information about configuration in containerized environments, see the [Autodiscovery Integration Templates][3] for guidance.

### Installation

Starting from Agent release 7.53.0, the Argo Rollouts check is included in the [Datadog Agent][2] package. No additional installation is needed in your environment.

This check uses [OpenMetrics][5] to collect metrics from the OpenMetrics endpoint that Karpenter exposes, which requires Python 3.

### Configuration

The Argo Rollouts controller has Prometheus-formatted metrics readily available at `/metrics` on port `8090`. For the Agent to start collecting metrics, the Argo Rollouts pods need to be annotated. For more information about annotations, refer to the [Autodiscovery Integration Templates][3] for guidance. You can find additional configuration options by reviewing the [sample argo_rollouts.d/conf.yaml][4].

**Note**: The listed metrics can only be collected if they are available. Some metrics are generated only when certain actions are performed. For example, the `argo_rollout.info.replicas.updated` metric is exposed only after a replica is updated.

The only parameter required for configuring the Argo Rollouts check is:
- `openmetrics_endpoint`: This parameter should be set to the location where the Prometheus-formatted metrics are exposed. The default port is `8090`. In containerized environments, `%%host%%` should be used for [host autodetection][3]. 

```yaml
apiVersion: v1
kind: Pod
# (...)
metadata:
  name: '<POD_NAME>'
  annotations:
    ad.datadoghq.com/argo-rollouts.checks: |
      {
        "argo_rollouts": {
          "init_config": {},
          "instances": [
            {
              "openmetrics_endpoint": "http://%%host%%:8090/metrics",
            }
          ]
        }
      }
    # (...)
spec:
  containers:
    - name: 'argo-rollouts'
# (...)
```

#### Log collection

_Available for Agent versions >6.0_

Argo Rollouts logs can be collected from the different Argo Rollouts pods through Kubernetes. Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][10].

See the [Autodiscovery Integration Templates][3] for guidance on applying the parameters below.

| Parameter      | Value                                                   |
| -------------- | ------------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "argo_rollouts", "service": "<SERVICE_NAME>"}`  |

### Validation

[Run the Agent's status subcommand][6] and look for `argo_rollouts` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Argo Rollouts integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://argoproj.github.io/rollouts/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/argo_rollouts/datadog_checks/argo_rollouts/data/conf.yaml.example
[5]: https://docs.datadoghq.com/integrations/openmetrics/
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/argo_rollouts/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/argo_rollouts/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.datadoghq.com/agent/kubernetes/log/
