# Agent Check: Infiniband

## Overview

This check monitors [Infiniband][1] through the Datadog Agent. 

This integration monitors data transfers by collecting counters and RDMA hardware counters from the Infiniband subsystem. It tracks performance metrics through the Linux kernel's Infiniband interface, which provides metric counters even when using alternative transports like RDMA over Converged Ethernet (RoCE).

Get visibility into your high-performance networking infrastructure to help identify bottlenecks and performance issues in data-intensive workloads. By monitoring both standard Infiniband counters and RDMA hardware counters, you'll get comprehensive insights into network throughput, errors, and packet statistics across your devices and ports.

Key metrics collected include port counters like bytes/packets transmitted and received, error counts, and RDMA hardware-specific metrics - giving operators the data needed to ensure optimal performance of their high-speed networking infrastructure.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. The check collects metrics by reading and submitting counters by default from [`/sys/class/infiniband/<device>/ports/*/counters/` and `/sys/class/infiniband/<device>/ports/*/hw_counters/`][3] directories. To ensure that this integration works, ensure that the Agent has the appropriate permissions to access and read the counters from these directories.

### Installation

The Infiniband check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `infiniband.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your infiniband performance data. See the [sample infiniband.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `infiniband` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Infiniband integration does not include any events.

### Service Checks

The Infiniband integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][8].


[1]: https://www.infinibandta.org/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.nvidia.com/networking/display/ofedv512580/infiniband+interface
[4]: https://github.com/DataDog/integrations-core/blob/master/infiniband/datadog_checks/infiniband/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/infiniband/metadata.csv
[8]: https://docs.datadoghq.com/help/
