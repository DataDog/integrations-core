# Agent Check: Keda

## Overview

This check monitors [Keda][1] through the Datadog Agent. For more information, see [Keda monitoring][10].

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

Starting from Agent release 7.62.0, the Keda check is included in the [Datadog Agent][2] package. No additional installation is needed in your environment.

### Configuration

Keda consists of multiple components, including the Admissions Controller, Metrics API Server, and the Operator. Each of these components can be scraped for metrics. Prometheus-formatted metrics are available at /metrics on port 8080 for each component.

To expose these metrics, ensure that Prometheus scraping is enabled for each component. For example, in Helm, you need to enable the following Helm configuration options:
- prometheus.metricServer.enabled
- prometheus.operator.enabled
- prometheus.webhooks.enabled

Alternatively, you can achieve this by providing the following configuration in a values.yaml file used during the Helm installation of Keda:

```yaml
prometheus:
  metricServer:
    enabled: true
  operator:
    enabled: true
  webhooks:
    enabled: true
```

For the Agent to start collecting metrics, the Keda controller pods need to be annotated. For more information about annotations, refer to the [Autodiscovery Integration Templates][3] for guidance. You can find additional configuration options by reviewing the [sample keda.d/conf.yaml][4]. 

**Note**: The listed metrics can only be collected if they are available. Some metrics are generated only when certain actions are performed. For example, the `keda.scaler.detail_errors.count` metric is exposed only after a scaler encountered an error.

The only parameter required for configuring the Keda check is:
- `openmetrics_endpoint`: This parameter should be set to the location where the Prometheus-formatted metrics are exposed. The default port is `8080`. In containerized environments, `%%host%%` should be used for [host autodetection][3]. 

```yaml
apiVersion: v1
kind: Pod
# (...)
metadata:
  name: '<POD_NAME>'
  annotations:
    ad.datadoghq.com/<CONTAINER_NAME>.checks: | # <CONTAINER_NAME> Needs to match the container name at the bottom. 'keda-operator-metrics-apiserver' in this example.
      {
        "keda": {
          "init_config": {},
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
    - name: <CONTAINER_NAME> # e.g. 'keda-operator-metrics-apiserver' in the Metrics API Server
# (...)
```

To collect metrics from each Keda component, the above pod annotations need to be applied to each Keda component pod. Example pod annotations for the Operator pod:

```yaml
# Pod manifest from a basic Helm chart deployment
apiVersion: v1
kind: Pod
# (...)
metadata:
  name: 'keda-operator'
  annotations:
    ad.datadoghq.com/<CONTAINER_NAME>.checks: |
      {
        "keda": {
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
    - name: keda-operator
# (...)
```
#### Log collection

_Available for Agent versions >6.0_

Kyverno logs can be collected from the different Keda pods through Kubernetes. Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][10].

See the [Autodiscovery Integration Templates][3] for guidance on applying the parameters below.

| Parameter      | Value                                                   |
| -------------- | ------------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "keda", "service": "<SERVICE_NAME>"}`  |

### Validation

[Run the Agent's status subcommand][6] and look for `keda` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Keda integration does not include any events.

### Service Checks

The Keda integration does not include any service checks.

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://keda.sh/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/keda/datadog_checks/keda/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/keda/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/keda/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://keda.sh/docs/2.16/integrations/prometheus/
[11]: https://github.com/kedacore/charts/blob/main/keda/README.md#operations
