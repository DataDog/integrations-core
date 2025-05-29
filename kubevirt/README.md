# KubeVirt Integration

## Overview

Get metrics from KubeVirt in real time to:

- Visualize and monitor KubeVirt states
- Monitor virtual machines running on Kubernetes
- Receive notifications about KubeVirt failovers and events

The Datadog KubeVirt integration monitors the various components of KubeVirt to provide comprehensive visibility into
your virtualized workloads running on Kubernetes.

For detailed information on each component, see:

- [KubeVirt API][1]
- [KubeVirt Controller][2]
- [KubeVirt Handler][3]

## Setup

### Installation

The KubeVirt integration consists of three main components, each included in the [Datadog Agent][4] package:

- **KubeVirt API**: Monitors the virt-api deployment
- **KubeVirt Controller**: Monitors the virt-controller deployment
- **KubeVirt Handler**: Monitors the virt-handler daemonset

For more information on installing the Datadog Agent on your Kubernetes clusters, see the [Kubernetes documentation][5].

### Configuration

For configuration instructions, see to the documentation of each integration:

- [KubeVirt API][1]
- [KubeVirt Controller][2]
- [KubeVirt Handler][3]

### Validation

Run the Agent's status subcommand and look for the respective KubeVirt components under the Checks section.

## Data Collected

### Metrics

See the metadata.csv files for a list of metrics provided by each integration:

- [KubeVirt API metadata.csv][6]
- [KubeVirt Controller metadata.csv][7]
- [KubeVirt Handler metadata.csv][8]

### Events

The KubeVirt integration does not include any events at this time.

### Service Checks

The KubeVirt integration includes service checks to verify connectivity to each component.

## Troubleshooting

Need help? Contact [Datadog support][9].

[1]: https://docs.datadoghq.com/integrations/kubevirt_api/
[2]: https://docs.datadoghq.com/integrations/kubevirt_controller/
[3]: https://docs.datadoghq.com/integrations/kubevirt_handler/
[4]: /account/settings/agent/latest
[5]: https://docs.datadoghq.com/agent/kubernetes/
[6]: https://github.com/DataDog/integrations-core/blob/master/kubevirt_api/metadata.csv
[7]: https://github.com/DataDog/integrations-core/blob/master/kubevirt_controller/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/kubevirt_handler/metadata.csv
[9]: https://docs.datadoghq.com/help/
