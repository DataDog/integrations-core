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

### Entity collection

Entity collection sends Argo CD Applications, Clusters, and Repositories to Datadog as resources, so that your Argo CD inventory is visible alongside the rest of your infrastructure. It is independent of metric and log collection, and it uses two complementary paths:

| Path                  | Mechanism                                                                        | Coverage                                                                                                       |
| --------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Agent collector       | The Agent's `argocd` check polls the Argo CD API on a fixed interval.            | Baseline inventory of Applications, Clusters, and Repositories.                                                 |
| Notifications webhook | The Argo CD [notifications controller][19] posts Application changes to Datadog. | Application sync, health, and operation changes between polls. These are also submitted as Datadog events.      |

Configure both paths. The Agent collector establishes and refreshes the full inventory, and the webhook carries the Application changes that happen between polls. Clusters and Repositories are collected only by the Agent, because Argo CD stores them as Kubernetes Secrets rather than custom resources and offers no notification trigger for them.

**Important**: Both paths identify an Application by the same key, built from the cluster name, the environment, the Application's namespace, and its name. The Agent derives the cluster name and environment from its own configuration, while the notifications controller reads them from its ConfigMap. If the two disagree, each path creates a separate resource for every Application, and neither path reports an error. Define both values once per cluster and reference them from both places.

**Note**: Entity collection requires Agent v7.82.0 or later.

#### Prerequisites

- Network access from the Agent to the Argo CD API server, which is usually the `argocd-server` service. This is the REST API, and it is distinct from the Prometheus endpoints used for metric collection.
- An Argo CD API token with read access to applications, clusters, and repositories. Add a dedicated local account to the `argocd-cm` ConfigMap, grant it read access in `argocd-rbac-cm`, then issue a token for it:

  ```yaml
  ## argocd-cm
  data:
    accounts.datadog: apiKey
  ```

  ```yaml
  ## argocd-rbac-cm
  data:
    policy.csv: |
      p, role:datadog-readonly, applications, get, */*, allow
      p, role:datadog-readonly, clusters, get, *, allow
      p, role:datadog-readonly, repositories, get, *, allow
      g, datadog, role:datadog-readonly
  ```

  ```shell
  argocd account generate-token --account datadog
  ```

  Patch these ConfigMaps rather than applying a partial manifest over them. Argo CD's installation manifest owns both, and applying a partial file replaces their entire `data` map. For more details, see [Argo CD user management][17] and [Argo CD RBAC configuration][18].

- The Argo CD notifications controller, which is bundled with Argo CD v2.6 and later. Earlier versions require the standalone `argocd-notifications` component.

#### Configure the Agent collector

Add the following to the Argo CD instance in `conf.d/argocd.d/conf.yaml`, alongside the metric collection endpoints you already configured. When the check is configured through Kubernetes Autodiscovery annotations instead, add the same keys to the instance in that configuration.

```yaml
init_config:

instances:
  - ## Existing metric collection endpoints, unchanged.
    app_controller_endpoint: http://argocd-metrics:8082/metrics
    api_server_endpoint: http://argocd-server-metrics:8083/metrics

    ## Entity collection against the Argo CD REST API.
    collect_genresources: true
    genresources_endpoint: https://argocd-server.argocd.svc.cluster.local
    genresources_auth_token: <ARGOCD_API_TOKEN>

    ## Poll all three resource types every five minutes.
    genresources_stream_applications_enabled: false
    genresources_application_full_scrape_interval_seconds: 300
    genresources_application_poll_interval_seconds: 300
    genresources_cluster_scrape_interval_seconds: 300
    genresources_repository_scrape_interval_seconds: 300
    genresources_ttl_seconds: 1800

    ## The check need not run every 15 seconds when the shortest interval above is 300.
    min_collection_interval: 60
```

The available options are:

| Option                                                 | Default  | Description                                                                                                                                                                                |
| ------------------------------------------------------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `collect_genresources`                                 | `false`  | Enables entity collection. Required.                                                                                                                                                       |
| `genresources_endpoint`                                | none     | Base URL of the Argo CD REST API. Required. This is not a Prometheus metrics URL.                                                                                                          |
| `genresources_auth_token`                              | none     | Bearer token used to authenticate against the Argo CD API. When unset, the collector uses the authentication configured on the instance.                                                    |
| `genresources_stream_applications_enabled`             | `true`   | Streams Application changes from the Argo CD API in near real time. Set it to `false` to poll instead and let the notifications webhook carry changes between polls.                        |
| `genresources_application_full_scrape_interval_seconds` | `600`    | Interval between full Application scrapes. Every Application is resubmitted, which refreshes its expiry.                                                                                    |
| `genresources_application_poll_interval_seconds`       | `120`    | Interval between Application polls that submit only what changed. Applies only when streaming is disabled. Set it to the full scrape interval to collect Applications on a single cadence.  |
| `genresources_cluster_scrape_interval_seconds`         | `300`    | Interval between full Cluster scrapes.                                                                                                                                                     |
| `genresources_repository_scrape_interval_seconds`      | `300`    | Interval between full Repository scrapes.                                                                                                                                                  |
| `genresources_ttl_seconds`                             | `1800`   | How long a resource is retained after it was last observed. Keep it at or above the longest scrape interval, otherwise resources expire before they are refreshed. The check logs a warning when this value is too low. |
| `genresources_max_resources_per_cycle`                 | `10000`  | Maximum number of items collected per resource type per cycle. Anything beyond the cap is dropped and a warning is logged.                                                                  |
| `collect_openmetrics`                                  | `true`   | Scrapes the Prometheus endpoints. Set it to `false` to run entity collection without metric collection, in which case the `*_endpoint` options are not required. At least one of `collect_openmetrics` and `collect_genresources` must be enabled. |

Keep the following in mind:

- Enable entity collection on one Argo CD instance only. Several Agents polling the same Argo CD API submit the same resources under the same key, which adds API load without adding data.
- The key prefix comes from the Agent's own cluster name and `env` tag, not from this configuration. Set `DD_CLUSTER_NAME` and `DD_ENV` explicitly when the Agent cannot detect them, such as when it runs outside the cluster it monitors, and use the same values in the notifications ConfigMap below.
- When the Argo CD API presents a certificate the Agent does not trust, point `tls_ca_cert` at the certificate authority. Setting `tls_verify` to `false` also works, but it disables verification for the whole instance.

#### Configure the notifications webhook

The Argo CD notifications controller renders a template and posts it to a webhook URL whenever a trigger fires. Point it at Datadog to push Application changes as they happen.

1. {{< integration-api-key-picker >}}
2. Add the context, destination, payload template, and trigger to the `argocd-notifications-cm` ConfigMap in the `argocd` namespace:

   ```yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: argocd-notifications-cm
     namespace: argocd
   data:
     ## Values available to the template below. These must match the cluster name
     ## and environment the Datadog Agent reports for this cluster.
     context: |
       cluster_name: <CLUSTER_NAME>
       env: <ENV>

     ## Destination. Paste the webhook URL generated above exactly as copied: it
     ## already carries the API key and the Argo CD integration selector.
     service.webhook.datadog: |
       url: <WEBHOOK_URL>
       headers:
       - name: Content-Type
         value: application/json

     ## Payload. The whole Application resource is sent, so every field Datadog
     ## reads is present without selecting fields here.
     template.dd-entity: |
       webhook:
         datadog:
           method: POST
           body: |
             {"dd":{"cluster_name":"{{ .context.cluster_name }}","env":"{{ .context.env }}"},"app":{{ toJson .app }}}

     ## When to send. The oncePer expression collapses repeats, so a stable
     ## Application is not notified again until its health, sync, or operation
     ## state changes.
     trigger.dd-on-change: |
       - when: app.status.health.status != '' or app.status.sync.status != ''
         oncePer: "app.status.health.status + '|' + app.status.sync.status + '|' + (app.status.operationState != nil ? app.status.operationState.phase : '')"
         send: [dd-entity]
   ```

   The webhook URL contains your API key, so treat the ConfigMap accordingly. To keep the key out of it, remove the `dd-api-key` query parameter from the URL and send the key as a `DD-API-KEY` header sourced from a Secret instead.

3. Apply the ConfigMap and restart the notifications controller so that it reloads the configuration:

   ```shell
   kubectl apply -f argocd-notifications-cm.yaml
   kubectl rollout restart deploy/argocd-notifications-controller -n argocd
   ```

4. Subscribe each Application you want to track:

   ```shell
   kubectl -n argocd annotate application <APP_NAME> \
     notifications.argoproj.io/subscribe.dd-on-change.datadog=""
   ```

   To subscribe every Application at once, add a default subscription to the same ConfigMap instead of annotating each one:

   ```yaml
     subscriptions: |
       - recipients: [datadog]
         triggers: [dd-on-change]
   ```

   A default subscription tracks every Application on the cluster. On large clusters, start with per-Application annotations, or add a `selector` to the default subscription, to keep event volume under control.

**Note**: Argo CD records the notifications it has already sent in each Application's `notified.notifications.argoproj.io` annotation and never removes entries. An Application therefore stops notifying once it has sent one notification for every combination its `oncePer` expression can produce, and the controller logs `already sent` in place of `TRIGGERED`. This deduplication is what keeps the webhook from firing on every reconcile, and the Agent collector's periodic scrape keeps the resource current regardless.

#### Validate entity collection

1. Confirm that the Agent reaches the Argo CD API. The check submits `argocd.genresources.api.up` with a value of `1` for each `resource_type` tag (`argocd_application`, `argocd_cluster`, and `argocd_repository`) when a scrape succeeds, and `0` when it fails.
2. Confirm that the notifications controller is sending notifications:

   ```shell
   kubectl logs -n argocd deploy/argocd-notifications-controller --tail=40 | grep -i trigger
   ```

   A line containing `TRIGGERED` means the trigger fired and the notification was sent.

3. Search the Datadog [Event Explorer][20] for `@evt.integration_id:argocd` to confirm that the webhook notifications arrived. A `202` response from Datadog means the notification was accepted rather than searchable, so allow a short delay before searching.
4. Confirm that each Application appears once in Datadog. Two resources for the same Application mean the cluster name or the environment differs between the Agent configuration and the notifications ConfigMap.

### Validation

[Run the Agent's status subcommand][6] and look for `argocd` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Argo CD integration submits Application sync and health status events to Datadog when the Argo CD [notifications controller][19] is configured to forward them through the webhook described in [Entity collection](#entity-collection).

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
[17]: https://argo-cd.readthedocs.io/en/stable/operator-manual/user-management/
[18]: https://argo-cd.readthedocs.io/en/stable/operator-manual/rbac/
[19]: https://argo-cd.readthedocs.io/en/stable/operator-manual/notifications/
[20]: https://docs.datadoghq.com/service_management/events/explorer/

