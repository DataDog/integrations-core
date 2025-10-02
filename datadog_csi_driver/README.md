# Agent Check: datadog_csi_driver

## Overview

This check monitors [`datadog_csi_driver`][1] through the Datadog Agent. 

The Datadog CSI Driver is a DaemonSet that runs a gRPC server implementing the CSI specifications on each node of your Kubernetes cluster.

Installing Datadog CSI driver on a Kubernetes cluster allows using CSI volumes by specifying the name of Datadog CSI driver.

The Datadog CSI node server is responsible for managing Datadog CSI volume lifecycle, allowing mounting UDS sockets for high performance dogstatsd and tracing without breaking constraints set by [`kubernetes pod security standards`][10]. 

The Datadog CSI Driver integration collects and monitors metrics from your Datadog CSI Driver, providing visibility into publish/unpublish requests and pod health for improved troubleshooting and performance monitoring.

**Minimum Agent version:** 7.70.1

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The `datadog_csi_driver` check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `datadog_csi_driver.d/conf.yaml` file, located in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your `datadog_csi_driver` performance data. See the [sample datadog_csi_driver.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and verify that `datadog_csi_driver` appears under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

This integration does not include any events.

### Service Checks

This integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][9].

[1]: https://docs.datadoghq.com/containers/csi_driver/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/datadog_csi_driver/datadog_checks/datadog_csi_driver/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/datadog_csi_driver/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/datadog_csi_driver/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://kubernetes.io/docs/concepts/security/pod-security-standards/
