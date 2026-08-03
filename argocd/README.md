# Agent Check: Argo CD

## Overview

This check monitors [Argo CD][1] through the Datadog Agent.

**Minimum Agent version:** 7.41.0

## Setup

### Installation

The Argo CD check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

**Note**: This check requires Agent v7.42.0+.

### Configuration

Argo CD exposes Prometheus-formatted metrics on three of their components:
   - Application Controller
   - API Server
   - Repo Server
   
The Datadog Agent can collect the exposed metrics using this integration. Follow the instructions below to configure data collection from any or all of the components.

**Note**: This check uses [OpenMetrics][11] for metric collection, which requires Python 3.

#### Containerized
##### Metric collection

Ensure that the Prometheus-formatted metrics are exposed in your Argo CD cluster. This is enabled by default if using Argo CD's [default manifests][10]. For the Agent to gather all metrics, each of the three aforementioned components needs to be annotated. For more information about annotations, see the [Autodiscovery Integration Templates][4] for guidance. Additional configuration options are available by reviewing the [sample argocd.d/conf.yaml][12].

There are use cases where Argo CD Applications contain labels that need to be exposed as Prometheus metrics. These labels are available using the `argocd_app_labels` metric, which is disabled on the Application Controller by default. Refer to the [ArgoCD Documentation][14] for instructions on how to enable it.

Example configurations:

**Application Controller**:
```yaml
apiVersion: v1
kind: Pod
# (...)
metadata:
  name: '<POD_NAME>'
  annotations:
    ad.datadoghq.com/argocd-application-controller.checks: |
      {
        "argocd": {
          "init_config": {},
          "instances": [
            {
              "app_controller_endpoint": "http://%%host%%:8082/metrics"
            }
          ]
        }
      }
    # (...)
spec:
  containers:
    - name: 'argocd-application-controller'
# (...)
```

**API Server**:
```yaml
apiVersion: v1
kind: Pod
# (...)
metadata:
  name: '<POD_NAME>'
  annotations:
    ad.datadoghq.com/argocd-server.checks: |
      {
        "argocd": {
          "init_config": {},
          "instances": [
            {
              "api_server_endpoint": "http://%%host%%:8083/metrics"
            }
          ]
        }
      }
    # (...)
spec:
  containers:
    - name: 'argocd-server'
# (...)
```

**Repo Server**:
```yaml
apiVersion: v1
kind: Pod
# (...)
metadata:
  name: '<POD_NAME>'
  annotations:
    ad.datadoghq.com/argocd-repo-server.checks: |
      {
        "argocd": {
          "init_config": {},
          "instances": [
            {
              "repo_server_endpoint": "http://%%host%%:8084/metrics"
            }
          ]
        }
      }
    # (...)
spec:
  containers:
    - name: 'argocd-repo-server'
# (...)
```

**Note**: For the full list of supported endpoints, see the [conf.yaml example file][15].

##### Troubleshooting 

**Clashing Tag Names**:
The Argo CD integration attaches a name tag derived from the application name OpenMetrics label when available. This could sometimes lead to querying issues if a name tag is already attached to a host, as seen in the example `name: host_a, app_a`. To prevent any unwanted behavior when querying, it is advisable to [remap the name label][13] to something more unique, such as `argocd_app_name` if the host happens to already have a name tag. Below is an example configuration:

**Application Controller**:
```yaml
apiVersion: v1
kind: Pod
# (...)
metadata:
  name: '<POD_NAME>'
  annotations:
    ad.datadoghq.com/argocd-application-controller.checks: |
      {
        "argocd": {
          "init_config": {},
          "instances": [
            {
              "app_controller_endpoint": "http://%%host%%:8082/metrics",
              "rename_labels": {
                "name": "argocd_app_name"
              }
            }
          ]
        }
      }
    # (...)
spec:
  containers:
    - name: 'argocd-application-controller'
# (...)
```

##### Log collection

_Available for Agent versions >6.0_

Argo CD logs can be collected from the different Argo CD pods through Kubernetes. Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][5].

See the [Autodiscovery Integration Templates][3] for guidance on applying the parameters below.

| Parameter      | Value                                                |
| -------------- | ---------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "argocd", "service": "<SERVICE_NAME>"}`  |

### Webhook Configuration

Configure the Argo CD [Notifications controller][1] to forward application sync and health events to Datadog through a webhook.

1. {{< integration-api-key-picker >}}
2. Add a `webhook.datadog` service to the `argocd-notifications-cm` ConfigMap, using the webhook URL generated above as the `url`.
3. Define a template and trigger in the same ConfigMap for the application events you want to send to Datadog (for example, sync or health status changes).
4. Subscribe the target `Application` resources to the trigger by adding the corresponding `notifications.argoproj.io/subscribe.<trigger>.datadog` annotation.
5. Apply the updated ConfigMap. Argo CD sends a notification to the endpoint the next time the trigger condition is met.

### Validation

[Run the Agent's status subcommand][6] and look for `argocd` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Argo CD integration submits application sync and health status events to Datadog when the Argo CD [Notifications controller][1] is configured to forward them through the webhook described in [Webhook Configuration](#webhook-configuration).

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].

## Further Reading

Additional helpful documentation, links, and articles:

- [Monitoring the health and performance of your container-native CI/CD pipelines][16]


[1]: https://argo-cd.readthedocs.io/en/stable/
[2]: /account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://docs.datadoghq.com/containers/kubernetes/integrations/?tab=kubernetesadv2
[5]: https://docs.datadoghq.com/agent/kubernetes/log/
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/argocd/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/argocd/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://argo-cd.readthedocs.io/en/stable/operator-manual/installation/
[11]: https://docs.datadoghq.com/integrations/openmetrics/
[12]: https://github.com/DataDog/integrations-core/blob/master/argocd/datadog_checks/argocd/data/conf.yaml.example
[13]: https://github.com/DataDog/integrations-core/blob/7.45.x/argocd/datadog_checks/argocd/data/conf.yaml.example#L164-L166
[14]: https://argo-cd.readthedocs.io/en/stable/operator-manual/metrics/#exposing-application-labels-as-prometheus-metrics
[15]: https://github.com/DataDog/integrations-core/blob/master/argocd/datadog_checks/argocd/data/conf.yaml.example#L45-L72
[16]: https://www.datadoghq.com/blog/container-native-ci-cd-integrations/

