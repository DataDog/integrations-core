# Cgroup Check

## Overview

The cgroup check lets you:

* Collect resource usage metrics for specific Linux control groups (cgroups): CPU, memory, I/O, etc

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host.

### Installation

The cgroup check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your server.

### Configuration

The cgroup check doesn't monitor anything by default; you must tell it which processes you want to monitor via the
`conf.yaml` configuration file.
The cgroup check takes the same options as the [process check](/integrations/process/).

### Validation

[Run the Agent's `status` subcommand][2] and look for `cgroup` under the Checks section.

## Data Collected
### Metrics

**Note**: Cgroup metrics are only available on Linux.

See [metadata.csv][3] for a list of metrics provided by this check.

All metrics are per `instance` configured in `cgroup.yaml`, and are tagged with `process_name:<instance_name>`
along with the `cgroup_path` and `cgroup_subsystem` being monitored.

### Events
The cgroup check does not include any events.

### Service Checks
The cgroup check does not include any service checks.

## Troubleshooting
Need help? Contact [Datadog support][4].

[1]: https://docs.datadoghq.com/monitoring/#process
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[3]: https://github.com/DataDog/integrations-core/blob/master/cgroup/metadata.csv
[4]: https://docs.datadoghq.com/help
