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

### Prerequisites

This check is part of GPU Monitoring and only runs when GPU monitoring is enabled on the Agent. Set `gpu.enabled` to `true` in `datadog.yaml` (or set the `DD_GPU_ENABLED` environment variable to `true`), following the [GPU Monitoring setup instructions][9]. If GPU monitoring is not enabled, the Agent skips this check and no InfiniBand metrics are collected.

### Configuration

1. To start collecting your InfiniBand performance data, create and edit the `infiniband.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory. See the [sample infiniband.d/conf.yaml][4] for all available configuration options.

2. This check works with minimal configuration. Configure optional parameters, which are provided to better control where the Agent looks for data and what data to collect if the default behaviors are not desired. Options include configuring the directory where counters reside, excluding specific devices/ports, and skipping or adding counters for collection.
```yaml
## All options defined here are available to all instances.
#
init_config:

    ## @param service - string - optional
    ## Attach the tag `service:<SERVICE>` to every metric, event, and service check emitted by this integration.
    ##
    ## Additionally, this sets the default `service` for every log source.
    #
    # service: <SERVICE>

## Every instance is scheduled independently of the others.
#
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
    ## These names come from the kernel's standard performance counter table and are the same across
    ## drivers, so they are stable.
    #
    # additional_counters:
    #   - symbol_error
    #   - port_xmit_wait

    ## @param additional_hw_counters - list of strings - optional
    ## A list of additional hardware counters to collect. The counter names are the files in which the
    ## counter values are stored. These are located inside
    ## /sys/class/infiniband/devices/<device>/ports/<port>/hw_counters.
    ##
    ## Unlike the standard counters, the contents of hw_counters are driver-specific and can also
    ## change with the device's mode, so there is no name that is valid everywhere. List the
    ## directory on the host to see what it actually exposes, and use the names from there:
    ##
    ##   ls /sys/class/infiniband/<device>/ports/<port>/hw_counters/
    ##
    ## Counter names that do not match a file are ignored. Run the check with debug logging to see
    ## which configured names were not found.
    #
    # additional_hw_counters:
    #   - additional_hw_counter

    ## @param exclude_counters - list of strings - optional
    ## A list of counters to exclude from the check. These are the standard counters found in
    ## /sys/class/infiniband/devices/<device>/ports/<port>/counters.
    #
    # exclude_counters:
    #   - VL15_dropped
    #   - link_downed

    ## @param exclude_hw_counters - list of strings - optional
    ## A list of hardware counters to exclude from the check. These are the driver-specific
    ## counters found in /sys/class/infiniband/devices/<device>/ports/<port>/hw_counters.
    #
    # exclude_hw_counters:
    #   - duplicate_request
    #   - out_of_sequence

    ## @param tags - list of strings - optional
    ## A list of tags to attach to every metric and service check emitted by this instance.
    ##
    ## Learn more about tagging at https://docs.datadoghq.com/tagging
    #
    # tags:
    #   - <KEY_1>:<VALUE_1>
    #   - <KEY_2>:<VALUE_2>

    ## @param service - string - optional
    ## Attach the tag `service:<SERVICE>` to every metric, event, and service check emitted by this integration.
    ##
    ## Overrides any `service` defined in the `init_config` section.
    #
    # service: <SERVICE>

    ## @param min_collection_interval - number - optional - default: 15
    ## This changes the collection interval of the check. For more information, see:
    ## https://docs.datadoghq.com/developers/write_agent_check/#collection-interval
    #
    # min_collection_interval: 15

    ## @param empty_default_hostname - boolean - optional - default: false
    ## This forces the check to send metrics with no hostname.
    ##
    ## This is useful for cluster-level checks.
    #
    # empty_default_hostname: false

    ## @param metric_patterns - mapping - optional
    ## A mapping of metrics to include or exclude, with each entry being a regular expression.
    ##
    ## Metrics defined in `exclude` will take precedence in case of overlap.
    #
    # metric_patterns:
    #   include:
    #   - <INCLUDE_REGEX>
    #   exclude:
    #   - <EXCLUDE_REGEX>
```

3. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `infiniband` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

This integration reads counters from the Linux RDMA/InfiniBand sysfs interface
at `/sys/class/infiniband`. Linux exposes RDMA devices through this interface
even when the port is using Ethernet/RoCE instead of native InfiniBand, so the
check can collect metrics from compatible RDMA NICs in either mode. Use the
`link_layer`, `netdev`, and `gid_type` tags to distinguish native InfiniBand
ports from Ethernet/RoCE-backed ports.

All metrics are tagged with `device` and `port`. When the kernel exposes the
corresponding sysfs files, metrics are also tagged with:

- `link_layer`, for example `link_layer:infiniband` or `link_layer:ethernet`
- `netdev` and `gid_type` from `gid_attrs`, for example `netdev:ens5f0` and `gid_type:roce_v2`
- `firmware_version`, `hca_type`, `board_id`, and `node_type` from device metadata

The check also submits `infiniband.port.rate` from each port's negotiated link
rate.

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
[9]: https://docs.datadoghq.com/gpu_monitoring/setup/
