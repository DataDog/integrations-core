# Agent Check: fluxcd

## Overview

This check monitors [Flux][1] through the Datadog Agent. Flux is a set of continuous and progressive delivery solutions for Kubernetes that is open and extensible.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

Starting from Agent release 7.51.0, the Fluxcd check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

For older versions of the Agent, [use these steps to install][10] the integration.


<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

##### Metric collection

1. Edit the `fluxcd.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Fluxcd performance data. See the [sample configuration file][4] for all available configuration options.

    This is an example configuration:

    ```yaml
    init_config:
      ...
    instances:
      - openmetrics_endpoint: http://<FLUXCD_ADDRESS>:8080/metrics
    ```

2. [Restart the Agent][5] after modifying the configuration.

<!-- xxz tab xxx -->
<!-- xxx tab "Docker" xxx -->

#### Docker

##### Metric collection

This is an example configuration of a Docker label inside `docker-compose.yml`. See the [sample configuration file][4] for all available configuration options.

```yaml
labels:
  com.datadoghq.ad.checks: '{"fluxcd":{"instances":[{"openmetrics_endpoint":"http://%%host%%:8080/metrics"}]}}'
```

<!-- xxz tab xxx -->
<!-- xxx tab "Kubernetes" xxx -->

#### Kubernetes

##### Metric collection

This is an example configuration with Kubernetes annotations on your Flux pods. See the [sample configuration file][4] for all available configuration options.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: '<POD_NAME>'
  annotations:
    ad.datadoghq.com/fluxcd.checks: |-
      {
        "fluxcd": {
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
    - name: 'fluxcd'
# (...)
```

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][6] and look for `fluxcd` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The fluxcd integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://fluxcd.io/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/7.51.x/fluxcd/datadog_checks/fluxcd/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/fluxcd/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/fluxcd/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.datadoghq.com/agent/guide/use-community-integrations/?tab=agentv721v621#installation
