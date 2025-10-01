# Agent Check: InfiniBand

## Overview

This check monitors [InfiniBand][1] through the Datadog Agent. 

This integration monitors data transfers by collecting counters and RDMA hardware counters from the InfiniBand subsystem. It tracks performance metrics through the Linux kernel's InfiniBand interface, which provides metric counters even when using alternative transports like RDMA over Converged Ethernet (RoCE).

Get visibility into your high-performance networking infrastructure to help identify bottlenecks and performance issues in data-intensive workloads. By monitoring both standard InfiniBand counters and RDMA hardware counters, you'll get comprehensive insights into network throughput, errors, and packet statistics across your devices and ports.

Key metrics collected include port counters like bytes/packets transmitted and received, error counts, and RDMA hardware-specific metrics - giving operators the data needed to ensure optimal performance of their high-speed networking infrastructure.

**Minimum Agent version:** 7.65.0

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. The check collects metrics by reading and submitting counters by default from [`/sys/class/infiniband/<device>/ports/*/counters/` and `/sys/class/infiniband/<device>/ports/*/hw_counters/`][3] directories. To ensure that this integration works, ensure that the Agent has the appropriate permissions to access and read the counters from these directories.

### Installation

The InfiniBand check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. To start collecting your InfiniBand performance data, create and edit the `infiniband.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory. See the [sample infiniband.d/conf.yaml][4] for all available configuration options.

2. This check works with minimal configuration. Configure optional parameters, which are provided to better control where the Agent looks for data and what data to collect if the default behaviors are not desired. Options include configuring the directory where counters reside, excluding specific devices/ports, and skipping or adding counters for collection.
```yaml
init_config:
instances:
  -
    ## @param infiniband_path - string - optional - default: /sys/class/infiniband
    ## The path to the infiniband directory.
    #
    # infiniband_path: /sys/class/infiniband

    ## @param exclude_devices - list of strings - optional
    ## A list of devices to exclude from the check. Devices are located in the infiniband directory. 
    ## The devices are located by default in /sys/class/infiniband.
    #
    # exclude_devices:
    #   - mlx5_0
    #   - efa0
    #   - ib1

    ## @param additional_counters - list of strings - optional
    ## A list of additional counters to collect. The counter names are the files in which the counter 
    ## values are stored. These are located inside /sys/class/infiniband/devices/<device>/ports/<port>/counters.
    #
    # additional_counters:
    #   - additional_counter
    #   - rx_mpwqe_frag

    ## @param additional_hw_counters - list of strings - optional
    ## A list of additional hardware counters to collect. The counter names are the files in which the 
    ## counter values are stored. These are located inside 
    ## /sys/class/infiniband/devices/<device>/ports/<port>/hw_counters.
    #
    # additional_hw_counters:
    #   - additional_hw_counter
    #   - rx_mpwqe_frag

    ## @param exclude_counters - list of strings - optional
    ## A list of counters to exclude from the check.
    #
    # exclude_counters:
    #   - duplicate_request
    #   - lifespan

    ## @param exclude_hw_counters - list of strings - optional
    ## A list of hardware counters to exclude from the check.
    #
    # exclude_hw_counters:
    #   - VL15_dropped
    #   - link_downed
```

3. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `infiniband` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The InfiniBand integration does not include any events.

### Service Checks

The InfiniBand integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][8].


[1]: https://www.infinibandta.org/
[2]: /account/settings/agent/latest
[3]: https://docs.nvidia.com/networking/display/ofedv512580/infiniband+interface
[4]: https://github.com/DataDog/integrations-core/blob/master/infiniband/datadog_checks/infiniband/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/infiniband/metadata.csv
[8]: https://docs.datadoghq.com/help/
