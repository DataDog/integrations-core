# Agent Check: traefik_mesh

## Overview

Traefik Mesh is a lightweight and easy-to-deploy service mesh that offers advanced traffic management, security, and observability features for microservices applications, leveraging the capabilities of Traefik Proxy. With Datadog's Traefik integration, you can:
- Obtain insights into the traffic entering your service mesh.
- Gain critical insights into the performance, reliability, and security of individual services within your mesh which ensures your services are operating efficiently while also helping to identify and resolve issues quickly.
- Gain detailed insights into the internal traffic flows within your service mesh which helps monitor performance and ensure reliability.

This check monitors [Traefik Mesh][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

Starting from Agent release v7.55.0, the Traefik Mesh check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

**Note**: This check requires Agent v7.55.0 or later.

### Configuration

Traefik Mesh can be configured to expose Prometheus-formatted metrics. The Datadog Agent can collect these metrics using the integration described below. Follow the instructions to configure data collection for your Traefik Mesh instances. For the required configurations to expose the Prometheus metrics, see the [Observability page in the official Traefik Mesh documentation][10].

In addition, a small subset of metrics can be collected by communicating with different API endpoints. Specifically:
- `/api/version`: Version information on the Traefik proxy.
- `/api/status/nodes`: Ready status of nodes visible by the Traefik [controller][5].
- `/api/status/readiness`: Ready status of the Traefik controller.

**Note**: This check uses [OpenMetrics][11] for metric collection, which requires Python 3.

#### Containerized
##### Metric collection

Make sure that the Prometheus-formatted metrics are exposed in your Traefik Mesh cluster. You can configure and customize this by following the instructions on the [Observability page in the official Traefik Mesh documentation][10]. In order for the Agent to start collecting metrics, the Traefik Mesh pods need to be annotated. For more information about annotations, refer to the [Autodiscovery Integration Templates][3] for guidance. You can find additional configuration options by reviewing the [`traefik_mesh.d/conf.yaml` sample][4].

**Note**: The following metrics can only be collected if they are available. Some metrics are generated only when certain actions are performed.

When configuring the Traefik Mesh check, you can use the following parameters:
- `openmetrics_endpoint`: This parameter should be set to the location where the Prometheus-formatted metrics are exposed. The default port is `8082`, but it can be configured using the `--entryPoints.metrics.address`. In containerized environments, `%%host%%` can be used for [host autodetection][3].
- `traefik_proxy_api_endpooint:` This parameter is optional. The default port is `8080` and can be configured using `--entryPoints.traefik.address`. In containerized environments, `%%host%%` can be used for [host autodetection][3].
- `traefik_controller_api_endpoint`: This parameter is optional. The default port is set to `9000`.

#### Traefik Proxy
```yaml
# (...)
metadata:
  name: '<POD_NAME>'
  annotations:
    ad.datadoghq.com/<CONTAINER_NAME>.checks: |
      {
        "traefik_mesh": {
          "init_config": {},
          "instances": [
            {
              "openmetrics_endpoint": "http://%%host%%:8082/metrics",
              "traefik_proxy_api_endpoint": "http://%%host%%:8080"
            }
          ]
        }
      }
    # (...)
spec:
  containers:
    - name: <CONTAINER_NAME>
# (...)
```

#### Traefik Controller
```yaml
# (...)
metadata:
  name: '<POD_NAME>'
  annotations:
    ad.datadoghq.com/<CONTAINER_NAME>.checks: |
      {
        "traefik_mesh": {
          "init_config": {},
          "instances": [
            {
              "traefik_controller_api_endpoint": "http://%%host%%:9000"
            }
          ]
        }
      }
    # (...)
spec:
  containers:
    - name: <CONTAINER_NAME>
# (...)
```

See the [sample traefik_mesh.d/conf.yaml][4] for all available configuration options.

### Log collection

_Available for Agent versions >6.0_

Traefik Mesh logs can be collected from the different Traefik Mesh pods through Kubernetes. Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][12].

See the [Autodiscovery Integration Templates][3] for guidance on applying the parameters below.

| Parameter      | Value                                                |
| -------------- | ---------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "traefik_mesh", "service": "<SERVICE_NAME>"}` |

### Validation

[Run the Agent's status subcommand][6] and look for `traefik_mesh` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Traefik Mesh integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://traefik.io/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/traefik_mesh/datadog_checks/traefik_mesh/data/conf.yaml.example
[5]: https://doc.traefik.io/traefik-mesh/api/
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/traefik_mesh/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/traefik_mesh/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://doc.traefik.io/traefik/observability/metrics/overview/
[11]: https://docs.datadoghq.com/integrations/openmetrics/
[12]: https://docs.datadoghq.com/containers/kubernetes/log/