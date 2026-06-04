# Agent Check: Kueue

## Overview

This check monitors Kueue through the Datadog Agent.

Kueue is a Kubernetes workload queueing system that allows you to manage and schedule workloads on your Kubernetes cluster. It provides a way to prioritize and manage workloads, and to ensure that workloads are scheduled in a fair and efficient manner. This integration collects metrics from the Kueue controller manager and the Kueue API server and enables you to monitor the health and performance of your Kueue cluster.

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

## Troubleshooting

Need help? Contact [Datadog support][8].


[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/kueue/datadog_checks/kueue/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/kueue/metadata.csv
[8]: https://docs.datadoghq.com/help/
[10]: https://docs.datadoghq.com/containers/cluster_agent/clusterchecks/?tab=helm#configuration-from-configuration-files
[11]: https://docs.datadoghq.com/containers/troubleshooting/cluster-and-endpoint-checks/#dispatching-logic-in-the-cluster-agent
