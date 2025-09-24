# Agent Check: Velero

## Overview

This check monitors [Velero][1] through the Datadog Agent. It collects data about Velero's backup, restore and snapshot operations. This allows users to gain insight into the health, performance and reliability of their disaster recovery processes.

**Minimum Agent version:** 7.64.0

## Setup

### Installation

The Velero check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

#### Metrics

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

Follow the instructions below to install and configure this check for an Agent running on a host. 

1. Edit the `velero.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Velero performance data. See the [sample velero.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

<!-- xxz tab xxx -->
<!-- xxx tab "Kubernetes" xxx -->

See the [Autodiscovery Integration Templates][3] for guidance on configuring this integration in a containerized environment.

Note that two types of pods need to be queried for all metrics to be collected: `velero` and `node-agent`
Therefore, make sure to update the annotations of the `velero` deployment as well as the `node-agent` daemonset.

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

#### Logs

The Velero integration can collect logs from the Velero pods.

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

To collect logs from Velero containers on a host:

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Uncomment and edit the logs configuration block in your `velero.d/conf.yaml` file. For example:

   ```yaml
   logs:
     - type: docker
       source: velero
       service: velero
   ```

<!-- xxz tab xxx -->
<!-- xxx tab "Kubernetes" xxx -->

To collect logs from a Velero Kubernetes deployment:

1. Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][10].

2. Set Log Integrations as pod annotations. This can also be configured with a file, a ConfigMap, or a key-value store. For more information, see the configuration section of [Kubernetes Log Collection][11].

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][6] and look for `velero` under the Checks section.

## Data Collected

### Metrics

This integration collects various Velero metrics, including:

- **Backup**: Success/failure rates, durations, and data sizes.
- **Restore**: Success/failure counts and validation failures.
- **Snapshot**: CSI and volume snapshot attempts, successes, and failures.
- **Pod volume data**: Upload/download success and failure rates. These are exposed by the `node-agent` pods.

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Velero integration does not include any events.

### Service Checks

The Velero integration does not include any service checks.

## Troubleshooting

Make sure that your Velero server is exposing metrics by checking that the feature is enabled in the deployment configuration:

```yaml
# Settings for Velero's prometheus metrics. Enabled by default.
metrics:
  enabled: true
  scrapeInterval: 30s
  scrapeTimeout: 10s
```

Need help? Contact [Datadog support][9].


[1]: https://velero.io
[2]: /account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/velero/datadog_checks/velero/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/velero/metadata.csv
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.datadoghq.com/agent/kubernetes/log/#setup
[11]: https://docs.datadoghq.com/agent/kubernetes/log/#configuration
