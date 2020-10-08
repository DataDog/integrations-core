# Agent Check: TCP Queue Length

## Overview

This check monitors the size of the Linux TCP receive and send queues.

## Setup

### Installation

`tcp_queue_length` is a core Agent 6/7 check that relies on an eBPF part implemented in `system-probe`.

The eBPF program used by `system-probe` is compiled at runtime and requires you to have access to the proper kernel headers.

On Debian-like distributions, install the kernel headers like this:
```sh
apt install -y linux-headers-$(uname -r)
```

On RHEL-like distributions, install the kernel headers like this:
```sh
yum install -y kernel-headers-$(uname -r)
```

### Configuration

Enabling the `tcp_queue_length` integration requires both the `system-probe` and the core agent to have the configuration option enabled.

Inside the `system-probe.yaml` configuration file, the following parameters must be set:
```yaml
system_probe_config:
  enabled: true
  enable_tcp_queue_length: true
```

1. Edit the `tcp_queue_length.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory to start collecting your tcp_queue_length performance data.
   See the [sample tcp_queue_length.d/conf.yaml][1] for all available configuration options.

    The `only_count_nb_contexts` parameter is enabled by default and collects only the number of timeseries it would normally collect. If disabled, the check will collect all data-- that is, the size of the TCP queues for every single connection.

2. [Restart the Agent][3].


### Configuration with Helm

With the [Datadog Helm chart][2], we must ensure that `system-probe` is activated by setting `datadog.systemProbe.enabled` to `true` in the `values.yaml` file.
Then, the check can be activated by setting the `datadog.systemProbe.enableTCPQueueLength` parameter.

### Validation

[Run the Agent's `status` subcommand][3] and look for `tcp_queue_length` under the checks section.

## Data Collected

### Metrics

For each TCP connection, `tcp_queue_length` collects the minimum and the maximum amount of data in the send and receive buffers between each data collection time point.

See [metadata.csv][4] for a list of metrics provided by this integration.

### Service Checks

The TCP Queue Length check does not include any service checks.

### Events

The TCP Queue Length check does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][5].

[1]: https://github.com/DataDog/datadog-agent/blob/master/cmd/agent/dist/conf.d/tcp_queue_length.d/conf.yaml.example
[2]: https://github.com/helm/charts/tree/master/stable/datadog
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[4]: https://github.com/DataDog/integrations-core/blob/master/tcp_queue_length/metadata.csv
[5]: https://docs.datadoghq.com/help/
