# Agent Check: Kueue

## Overview

This check monitors [Kueue][1] through the Datadog Agent. 

Include a high level overview of what this integration does:
- What does your product do (in 1-2 sentences)?
- What value will customers get from this integration, and why is it valuable to them?
- What specific data will your integration monitor, and what's the value of that data?

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Kueue check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

Kueue is a cluster-level service. Configure this integration as a Cluster Agent cluster check so only one Agent instance scrapes the Kueue metrics endpoint.

1. To collect optional ClusterQueue resource metrics, such as `kueue.cluster_queue.resource_usage.gpu`, configure Kueue with `metrics.enableClusterQueueResources: true` and restart the Kueue controller manager.

2. Provide a [cluster check configuration][10] to the Cluster Agent. For file or ConfigMap based configuration, set `cluster_check: true` in the instance:

   ```yaml
   clusterAgent:
     confd:
       kueue.yaml: |-
         cluster_check: true
         init_config:
         instances:
         - openmetrics_endpoint: http://kueue-controller-manager-metrics-service.kueue-system.svc:8080/metrics
   ```

3. Alternatively, annotate the Kueue metrics service with Autodiscovery cluster check annotations:

   ```yaml
   ad.datadoghq.com/endpoints.checks: |
     {
       "kueue": {
         "instances": [
           {
             "openmetrics_endpoint": "http://%%host%%:%%port%%/metrics"
           }
         ]
       }
     }
   ```

See the [sample kueue.d/conf.yaml][4] for all available configuration options.

### Validation

[Run the Cluster Agent's `clusterchecks` subcommand][11] and look for `kueue` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Kueue integration does not include any events.

### Service Checks

The Kueue integration does not include any service checks.

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/kueue/datadog_checks/kueue/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/kueue/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/kueue/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.datadoghq.com/containers/cluster_agent/clusterchecks/?tab=helm#configuration-from-configuration-files
[11]: https://docs.datadoghq.com/containers/troubleshooting/cluster-and-endpoint-checks/#dispatching-logic-in-the-cluster-agent
