# Agent Check: karpenter

## Overview

This check monitors [Karpenter][1] through the Datadog Agent. For more information, see [Karpenter monitoring][10].

## Setup

Follow the instructions below to install and configure this check for an Agent running in your Kubernetes environment. For more information about configuration in containerized environments, see the [Autodiscovery Integration Templates][3] for guidance.

### Installation

Starting from Agent release 7.50.0, the Karpenter check is included in the [Datadog Agent][2] package. No additional installation is needed in your environment.

This check uses [OpenMetrics][5] to collect metrics from the OpenMetrics endpoint that Karpenter exposes, which requires Python 3.

### Configuration

#### Metric collection

Make sure that the Prometheus-formatted metrics are exposed in your Karpenter cluster and on which port. You can configure the port by following the instructions on the [Metrics][10] page in the Karpenter documentation. For the Agent to start collecting metrics, the Karpenter pods need to be annotated. For more information about annotations, refer to the [Autodiscovery Integration Templates][3] for guidance. You can find additional configuration options by reviewing the [sample karpenter.d/conf.yaml][4].

**Note**: The listed metrics can only be collected if they are available. Some metrics are generated only when certain actions are performed. For example, the `karpenter.nodes.terminated` metric is exposed only after a node is terminated.

The only parameter required for configuring the Karpenter check is:
- `openmetrics_endpoint`: This parameter should be set to the location where the Prometheus-formatted metrics are exposed. The default port is `8000`, but it can be configured using the `METRICS_PORT` [environment variable][10]. In containerized environments, `%%host%%` should be used for [host autodetection][3]. 

```yaml
apiVersion: v1
kind: Pod
# (...)
metadata:
  name: '<POD_NAME>'
  annotations:
    ad.datadoghq.com/controller.checks: |
      {
        "karpenter": {
          "init_config": {},
          "instances": [
            {
              "openmetrics_endpoint": "http://%%host%%:8000/metrics"
            }
          ]
        }
      }
    # (...)
spec:
  containers:
    - name: 'controller'
# (...)
```

#### Log collection

_Available for Agent versions >6.0_

Karpenter logs can be collected from the different Karpenter pods through Kubernetes. Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][11].

See the [Autodiscovery Integration Templates][3] for guidance on applying the parameters below.

| Parameter      | Value                                                   |
| -------------- | ------------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "karpenter", "service": "<SERVICE_NAME>"}`  |

### Validation

[Run the Agent's status subcommand][6] and look for `karpenter` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Karpenter integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].

## Further Reading

Additional helpful documentation, links, and articles:

- [Monitoring your container-native technologies][12]


[1]: https://karpenter.sh/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/karpenter/datadog_checks/karpenter/data/conf.yaml.example
[5]: https://docs.datadoghq.com/integrations/openmetrics/
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/?tab=agentv6v7#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/karpenter/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/karpenter/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://karpenter.sh/docs/reference/metrics/
[11]: https://docs.datadoghq.com/agent/kubernetes/log/
[12]: https://www.datadoghq.com/blog/container-native-integrations/#autoscaling-and-resource-utilization-with-karpenter
