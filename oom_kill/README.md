# Agent Check: OOM Kill

## Overview

This check monitors the kernel OOM (out of memory) kill process through the Datadog Agent and the System Probe.

## Setup

### Installation

The OOM Kill check is included in the [Datadog Agent][1] package. It relies on an eBPF program implemented in the System Probe.

The eBPF program used by the System Probe is compiled at runtime and requires you to have access to the proper kernel headers.

On Debian-like distributions, install the kernel headers like this:
```sh
apt install -y linux-headers-$(uname -r)
```

On RHEL-like distributions, install the kernel headers like this:
```sh
yum install -y kernel-headers-$(uname -r)
```

### Configuration

1. Ensure that the `oom_kill.d/conf.yaml` file is present in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your OOM Kill metrics.

2. Ensure the following configuration is set in `system_probe.yaml`:

```yaml
system_probe_config:
    enabled: true
    enable_oom_kill: true
```

3. [Restart the Agent][2].

### Configuration with Helm

With the [Datadog Helm chart][3], ensure that the `datadog.systemProbe` and `datadog.systemProbe.enableOOMKill` parameters are enabled in the `values.yaml` file.

### Validation

[Run the Agent's status subcommand][4] and look for `oom_kill` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this check.

### Service Checks

The OOM Kill check does not include any service checks.

### Events

The OOM Kill check submits an event for each OOM Kill that includes the killed process ID and name, as well as the triggering process ID and name.

## Troubleshooting

Need help? Contact [Datadog support][6].

[1]: https://docs.datadoghq.com/agent/guide/
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[3]: https://github.com/helm/charts/tree/master/stable/datadog
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/oom_kill/metadata.csv
[6]: https://docs.datadoghq.com/help/
