# Agent Check: TorchServe

## Overview

This check monitors [TorchServe][1] through the Datadog Agent. 

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

Starting from Agent release 7.47.0, the TorchServe check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

<div class="alert alert-warning">This check uses <a href="https://docs.datadoghq.com/integrations/openmetrics/">OpenMetrics</a> to collect metrics from the OpenMetrics endpoint TorchServe can expose, which requires Python 3.</div>

### Prerequisites

The TorchServe check collects TorchServe's metrics and performance data using three different endpoints:
   - The [Inference API][14] to collect the overall health status of your TorchServe instance.
   - The [Management API][13] to collect metrics on the various models you are running.
   - The [OpenMetrics endpoint][15] exposed by TorchServe.

You can configure these endpoints using the `config.properties` file, as described in [the TorchServe documentation][10]. For example:

```
inference_address=http://0.0.0.0:8080
management_address=http://0.0.0.0:8081
metrics_address=http://0.0.0.0:8082
metrics_mode=prometheus
number_of_netty_threads=32
default_workers_per_model=10
job_queue_size=1000
model_store=/home/model-server/model-store
workflow_store=/home/model-server/wf-store
load_models=all
```

This configuration file exposes the three different endpoints that can be used by the integration to monitor your instance.

#### OpenMetrics endpoint

To enable the Prometheus endpoint, you need to configure two options: 

- `metrics_address`: Metrics API binding address. Defaults to `http://127.0.0.1:8082`
- `metrics_mode`: Two metric modes are supported by TorchServe: `log` and `prometheus`. Defaults to `log`. You have to set it to `prometheus` to collect metrics from this endpoint.

For instance:

```
metrics_address=http://0.0.0.0:8082
metrics_mode=prometheus
```

In this case, the OpenMetrics endpoint is exposed at this URL: `http://<TORCHSERVE_ADDRESS>:8082/metrics`.

### Configuration

These three different endpoints can be monitored independently and must be configured separately in the configuration file, one API per instance. See the [sample torchserve.d/conf.yaml][4] for all available configuration options.

<!-- xxx tabs xxx -->
<!-- xxx tab "OpenMetrics endpoint" xxx -->
#### Configure the OpenMetrics endpoint

Configuration options for the OpenMetrics endpoint can be found in the configuration file under the `TorchServe OpenMetrics endpoint configuration` section. The minimal configuration only requires the `openmetrics_endpoint` option:

```yaml
init_config:
  ...
instances:
  - openmetrics_endpoint: http://<TORCHSERVE_ADDRESS>:8082/metrics
```

For more options, see the [sample `torchserve.d/conf.yaml` file][4].

TorchServe allows the custom service code to emit [metrics that will be available based on the configured `metrics_mode`][11]. You can configure this integration to collect these metrics using the `extra_metrics` option. These metrics will have the `torchserve.openmetrics` prefix, just like any other metrics coming from this endpoint.

<div class="alert alert-info">These custom TorchServe metrics are considered standard metrics in Datadog.</div>

<!-- xxz tab xxx -->
<!-- xxx tab "Inference API" xxx -->
#### Configure the Inference API

This integration relies on the [Inference API][14] to get the overall status of your TorchServe instance. Configuration options for the Inference API can be found in the [configuration file][4] under the `TorchServe Inference API endpoint configuration` section. The minimal configuration only requires the `inference_api_url` option:

```yaml
init_config:
  ...
instances:
  - inference_api_url: http://<TORCHSERVE_ADDRESS>:8080
```

This integration leverages the [Ping endpoint][12] to collect the overall health status of your TorchServe server.

<!-- xxz tab xxx -->
<!-- xxx tab "Management API" xxx -->
#### Configure the Management API

You can collect metrics related to the models that are currently running in your TorchServe server using the [Management API][13]. Configuration options for the Inference API can be found in the [configuration file][4] under the `TorchServe Management API endpoint configuration` section. The minimal configuration only requires the `management_api_url` option:

```yaml
init_config:
  ...
instances:
  - management_api_url: http://<TORCHSERVE_ADDRESS>:8081
```

By default, the integration collects data from every single models, up to 100 models. This can be modified using the `limit`, `include`, and `exclude` options. For example:

```yaml
init_config:
  ...
instances:
  - management_api_url: http://<TORCHSERVE_ADDRESS>:8081
    limit: 25
    include: 
      - my_model.* 
```

This configuration only collects metrics for model names that match the `my_model.*` regular expression, up to 25 models. 

You can also exclude some models:

```yaml
init_config:
  ...
instances:
  - management_api_url: http://<TORCHSERVE_ADDRESS>:8081
    exclude: 
      - test.* 
```

This configuration collects metrics for every model name that does not match the `test.*` regular expression, up to 100 models.

<div class="alert alert-info">You can use the `include` and `exclude` options in the same configuration. The `exclude` filters are applied after the `include` ones.</div>

By default, the integration retrieves the full list of the models every time the check runs. You can cache this list by using the `interval` option for increased performance of this check. 

<div class="alert alert-warning">Using the `interval` option can also delay some metrics and events.</div>

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

#### Complete configuration 

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

This example demonstrates the complete configuration leveraging the three different APIs described in the previous sections:

```yaml
init_config:
  ...
instances:
  - openmetrics_endpoint: http://<TORCHSERVE_ADDRESS>:8082/metrics
    # Also collect your own TorchServe metrics
    extra_metrics:
      - my_custom_torchserve_metric
  - inference_api_url: http://<TORCHSERVE_ADDRESS>:8080
  - management_api_url: http://<TORCHSERVE_ADDRESS>:8081
    # Include all the model names that match this regex   
    include:
      - my_models.*
    # But exclude all the ones that finish with `-test`
    exclude: 
      - .*-test 
    # Refresh the list of models only every hour
    interval: 3600
```

[Restart the Agent][5] after modifying the configuration.

<!-- xxz tab xxx -->
<!-- xxx tab "Docker" xxx -->

This example demonstrates the complete configuration leveraging the three different APIs described in the previous sections as a Docker label inside `docker-compose.yml`:

```yaml
labels:
  com.datadoghq.ad.checks: '{"torchserve":{"instances":[{"openmetrics_endpoint":"http://%%host%%:8082/metrics","extra_metrics":["my_custom_torchserve_metric"]},{"inference_api_url":"http://%%host%%:8080"},{"management_api_url":"http://%%host%%:8081","include":["my_models.*"],"exclude":[".*-test"],"interval":3600}]}}'
```

<!-- xxz tab xxx -->
<!-- xxx tab "Kubernetes" xxx -->

This example demonstrates the complete configuration leveraging the three different APIs described in the previous sections as Kubernetes annotations on your Torchserve pods:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: '<POD_NAME>'
  annotations:
    ad.datadoghq.com/torchserve.checks: |-
      {
        "torchserve": {
          "instances": [
            {
              "openmetrics_endpoint": "http://%%host%%:8082/metrics",
              "extra_metrics": [
                "my_custom_torchserve_metric"
              ]
            },
            {
              "inference_api_url": "http://%%host%%:8080"
            },
            {
              "management_api_url": "http://%%host%%:8081",
              "include": [
                ".*"
              ],
              "exclude": [
                ".*-test"
              ],
              "interval": 3600
            }
          ]
        }
      }
    # (...)
spec:
  containers:
    - name: 'torchserve'
# (...)
```

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][6] and look for `torchserve` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration. 

Metrics are prefixed using the API they are coming from:
- `torchserve.openmetrics.*` for metrics coming from the OpenMetrics endpoint.
- `torchserve.inference_api.*` for metrics coming from the Inference API.
- `torchserve.management_api.*` for metrics coming from the Management API.

### Events

The TorchServe integration include three events using the Management API:

- `torchserve.management_api.model_added`: This event fires when a new model has been added.
- `torchserve.management_api.model_removed`: This event fires when a model has been removed.
- `torchserve.management_api.default_version_changed`: This event fires when a default version has been set for a given model.

<div class="alert alert-info">You can disable the events setting the `submit_events` option to `false` in your <a href="https://github.com/DataDog/integrations-core/blob/master/torchserve/datadog_checks/torchserve/data/conf.yaml.example">configuration file</a>.</div>

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

### Logs

The TorchServe integration can collect logs from the TorchServe service and forward them to Datadog. 

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Uncomment and edit the logs configuration block in your `torchserve.d/conf.yaml` file. Here's an example:

   ```yaml
   logs:
     - type: file
       path: /var/log/torchserve/model_log.log
       source: torchserve
       service: torchserve
     - type: file
       path: /var/log/torchserve/ts_log.log
       source: torchserve
       service: torchserve
   ```

See [the example configuration file][4] on how to collect all logs.

For more information about the logging configuration with TorchServe, see the [official TorchServe documentation][16].

<div class="alert alert-warning">You can also collect logs from the `access_log.log` file. However, these logs are included in the `ts_log.log` file, leading you to duplicated logs in Datadog if you configure both files.</div>

## Troubleshooting

Need help? Contact [Datadog support][9].

[1]: https://pytorch.org/serve/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/torchserve/datadog_checks/torchserve/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/torchserve/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/torchserve/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://pytorch.org/serve/configuration.html#configure-torchserve-listening-address-and-port
[11]: https://pytorch.org/serve/metrics.html#custom-metrics-api
[12]: https://pytorch.org/serve/inference_api.html#health-check-api
[13]: https://pytorch.org/serve/management_api.html
[14]: https://pytorch.org/serve/inference_api.html
[15]: https://pytorch.org/serve/metrics_api.html
[16]: https://pytorch.org/serve/logging.html?highlight=logs