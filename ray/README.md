# Agent Check: Ray

## Overview

This check monitors [Ray][1] through the Datadog Agent. Ray is an open-source unified compute framework that makes it easy to scale AI and Python workloads, from reinforcement learning to deep learning to tuning, and model serving.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

Starting from Agent release 7.49.0, the Ray check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

**WARNING**: This check uses [OpenMetrics](https://docs.datadoghq.com/integrations/openmetrics/) to collect metrics from the OpenMetrics endpoint Ray can expose, which requires Python 3.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

##### Metric collection

1. Edit the `ray.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Ray performance data. See the [sample configuration file][4] for all available configuration options.

    This example demonstrates the configuration:

    ```yaml
    init_config:
      ...
    instances:
      - openmetrics_endpoint: http://<RAY_ADDRESS>:8080
    ```

2. [Restart the Agent][5] after modifying the configuration.

<!-- xxz tab xxx -->
<!-- xxx tab "Docker" xxx -->

#### Docker

##### Metric collection

This example demonstrates the configuration as a Docker label inside `docker-compose.yml`. See the [sample configuration file][4] for all available configuration options.

```yaml
labels:
  com.datadoghq.ad.checks: '{"ray":{"instances":[{"openmetrics_endpoint":"http://%%host%%:8080"}]}}'
```

<!-- xxz tab xxx -->
<!-- xxx tab "Kubernetes" xxx -->

#### Kubernetes

##### Metric collection

This example demonstrates the configuration as Kubernetes annotations on your Ray pods. See the [sample configuration file][4] for all available configuration options.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: '<POD_NAME>'
  annotations:
    ad.datadoghq.com/ray.checks: |-
      {
        "ray": {
          "instances": [
            {
              "openmetrics_endpoint": "http://%%host%%:8080"
            }
          ]
        }
      }
    # (...)
spec:
  containers:
    - name: 'ray'
# (...)
```

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

Ray metrics are available on the OpenMetrics endpoint. Additionally, Ray allows you to [export custom application-level metrics][10]. You can configure the Ray integration to collect these metrics using the `extra_metrics` option. All Ray metrics, including your custom metrics, use the `ray.` prefix.

**Note:** Custom Ray metrics are considered standard metrics in Datadog.

This example demonstrates a configuration leveraging the `extra_metrics` option:

```yaml
init_config:
  ...
instances:
  - openmetrics_endpoint: http://<RAY_ADDRESS>:8080
    # Also collect your own Ray metrics
    extra_metrics:
      - my_custom_ray_metric
```

More info on how to configure this option can be found in the [sample `ray.d/conf.yaml` configuration file][11].

### Validation

[Run the Agent's status subcommand][6] and look for `ray` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Ray integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

### Logs

The Ray integration can collect logs from the Ray service and forward them to Datadog. 

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Uncomment and edit the logs configuration block in your `ray.d/conf.yaml` file. Here's an example:

   ```yaml
   logs:
     - type: file
       path: /tmp/ray/session_latest/logs/dashboard.log
       source: ray
       service: ray
     - type: file
       path: /tmp/ray/session_latest/logs/gcs_server.out
       source: ray
       service: ray
   ```

<!-- xxz tab xxx -->
<!-- xxx tab "Kubernetes" xxx -->

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][13].

Then, set Log Integrations as pod annotations. This can also be configured with a file, a configmap, or a key-value store. For more information, see the configuration section of [Kubernetes Log Collection][14].


**Annotations v1/v2**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: ray
  annotations:
    ad.datadoghq.com/apache.logs: '[{"source":"ray","service":"ray"}]'
spec:
  containers:
    - name: ray
```

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

For more information about the logging configuration with Ray and all the log files, see the [official Ray documentation][12].

## Troubleshooting

Need help? Contact [Datadog support][9].

[1]: https://www.ray.io/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/ray/datadog_checks/ray/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/ray/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/ray/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.ray.io/en/latest/ray-observability/user-guides/add-app-metrics.html
[11]: https://github.com/DataDog/integrations-core/blob/master/ray/datadog_checks/ray/data/conf.yaml.example#L59-L105 
[12]: https://docs.ray.io/en/latest/ray-observability/user-guides/configure-logging.html
[13]: https://docs.datadoghq.com/agent/kubernetes/log/#setup
[14]: https://docs.datadoghq.com/agent/kubernetes/log/#configuration
