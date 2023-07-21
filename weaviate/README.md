# Agent Check: Weaviate

## Overview

This check monitors [Weaviate][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Weaviate check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

**Note**: This check requires Agent v7.47.0 or later.

### Configuration

Weaviate can be configured to expose Prometheus-formatted metrics. The Datadog Agent can collect these metrics using the integration described below. Follow the instructions to configure data collection for your Weaviate instances. For the required configurations to expose the Prometheus metrics, see the [Monitoring][10] page in the Weaviate documentation.

In addition, a small subset of metrics can be collected by communicating with different [API endpoints][11]. Specifically:
- `/v1/meta`: Version information
- `/v1/nodes`: Node-specific metrics such as objects and shards
- `/v1/.well-known`: HTTP response time and service liveness

**Note**: This check uses [OpenMetrics][12] for metric collection, which requires Python 3.

#### Containerized
##### Metric collection

Make sure that the Prometheus-formatted metrics are exposed in your Weaviate cluster. You can configure and customize this by following the instructions on the [Monitoring][10] page in the Weaviate documentation. For the Agent to start collecting metrics, the Weaviate pods need to be annotated. For more information about annotations, refer to the [Autodiscovery Integration Templates][3] for guidance. You can find additional configuration options by reviewing the [sample weaviate.d/conf.yaml][4]

**Note**: The listed metrics can only be collected if they are available. Some metrics are generated only when certain actions are performed. For example, the object deletion metric is exposed only when an object is deleted.

The two most important parameters for configuring the Weaviate check are as follows:
- `openmetrics_endpoint`: This parameter should be set to the location where the Prometheus-formatted metrics are exposed. The default port is `2112`, but it can be configured using the `PROMETHEUS_MONITORING_PORT` [environment variable][10]. In containerized environments, `%%host%%` can be used for [host autodetection][3]. 
- `weaviate_api_endpoint`: This parameter is optional. By default, this parameter is set to `<hostname>:8080` and it specifies the configuration of the [RESTful API][11].

If authentication is required for the RESTful API endpoints, the check can be configured to provide an API key as part of the [request header][13].


```yaml
apiVersion: v1
kind: Pod
# (...)
metadata:
  name: '<POD_NAME>'
  annotations:
    ad.datadoghq.com/weaviate.checks: |
      {
        "weaviate": {
          "init_config": {},
          "instances": [
            {
              "openmetrics_endpoint": "http://%%host%%:2112/metrics",
              "weaviate_api_endpoint": "http://%%host%%:8080",
              "headers": {'Authorization': 'Bearer if_needed_for_auth'}
            }
          ]
        }
      }
    # (...)
spec:
  containers:
    - name: 'weaviate'
# (...)
```

### Validation

[Run the Agent's status subcommand][6] and look for `weaviate` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Weaviate integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/weaviate/datadog_checks/weaviate/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/weaviate/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/weaviate/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://weaviate.io/developers/weaviate/configuration/monitoring
[11]: https://weaviate.io/developers/weaviate/api/rest
[12]: https://docs.datadoghq.com/integrations/openmetrics/
[13]: https://github.com/DataDog/integrations-core/blob/7.46.x/openmetrics/datadog_checks/openmetrics/data/conf.yaml.example#L544-L546