# Agent Check: Kubeflow

## Overview

This check monitors [Kubeflow][1] through the Datadog Agent. 


## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Kubeflow check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `kubeflow.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your kubeflow performance data. See the [sample kubeflow.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

#### Metric collection

Make sure that the Prometheus-formatted metrics are exposed for your `kubeflow` componenet. 
For the Agent to start collecting metrics, the `kubeflow` pods need to be annotated.

Kubeflow has metrics endpoints that can be accessed on port `9090`. 

**Note**: The listed metrics can only be collected if they are available(depending on the version). Some metrics are generated only when certain actions are performed. 

The only parameter required for configuring the `kubeflow` check is `openmetrics_endpoint`. This parameter should be set to the location where the Prometheus-formatted metrics are exposed. The default port is `9090`. In containerized environments, `%%host%%` should be used for [host autodetection][3]. 

```yaml
apiVersion: v1
kind: Pod
# (...)
metadata:
  name: '<POD_NAME>'
  annotations:
    ad.datadoghq.com/controller.checks: |
      {
        "kubeflow": {
          "init_config": {},
          "instances": [
            {
              "openmetrics_endpoint": "http://%%host%%:9090/metrics"
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

### Validation

[Run the Agent's status subcommand][6] and look for `kubeflow` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Kubeflow integration does not include any events.

### Service Checks

The Kubeflow integration does not include any service checks.

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/kubeflow/datadog_checks/kubeflow/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/kubeflow/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/kubeflow/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
