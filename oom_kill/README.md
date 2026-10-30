# Agent Check: OOM Kill

## Overview

This check monitors the kernel OOM (out of memory) kill process through the Datadog Agent and the System Probe.

## Setup

### Installation

The OOM Kill check is included in the [Datadog Agent][1] package. It relies on an eBPF program implemented in the System Probe.

The eBPF program used by the System Probe is compiled at runtime and requires you to have access to the proper kernel headers.

On Host and Docker installations, install the kernel headers:

- Debian-like distributions:
  ```sh
  apt install -y linux-headers-$(uname -r)
  ```
- RHEL-like distributions:
  ```sh
  yum install -y kernel-headers-$(uname -r)
  yum install -y kernel-devel-$(uname -r)
  ```

**Note**: Kernel version 4.9 or later is required for the OOM Kill check to work.
In addition, Windows and CentOS/RHEL versions earlier than 8 are not supported.

### Configuration
<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host
1. In the `system-probe.yaml` file at the root of your Agent's configuration directory, add the following configuration:

    ```yaml
    system_probe_config:
      enable_oom_kill: true
    ```

2. The Agent has a pre-packaged [`oom_kill.d/conf.yaml.default`][2] file that is used when the check is enabled in the `system-probe.yaml`. This is in the `conf.d/` folder at the root of your Agent's configuration directory. You can create a custom `oom_kill.d/conf.yaml` file to change the configuration options.

3. [Restart the Agent][3].
<!-- xxz tab xxx -->
<!-- xxx tab "Docker" xxx -->

#### Docker

1. Start the Agent container with the environment variable to enable the check in the System Probe process. This uses the pre-packaged [`oom_kill.d/conf.yaml.default`][2] once enabled:
    ```
    -e DD_SYSTEM_PROBE_CONFIG_ENABLE_OOM_KILL=true
    ```

2. Mount the following volumes to the Agent container:

    ```
    -v /sys/kernel/debug:/sys/kernel/debug
    -v /lib/modules:/lib/modules
    -v /usr/src:/usr/src
    ```

3. Add the following permission to enable BPF operations:

    ```
    --privileged
    ```

    From kernel version 5.8, the `--privileged` parameter can be replaced by `--cap-add CAP_BPF`.

**Note**: `--privileged` mode is not supported in Docker swarm.

<!-- xxz tab xxx -->
<!-- xxx tab "Kubernetes" xxx -->

#### Kubernetes

##### Datadog Operator

Set the `features.oomKill.enabled` parameter in the `DatadogAgent` manifest:
```yaml
apiVersion: datadoghq.com/v2alpha1
kind: DatadogAgent
metadata:
  name: datadog
spec:
  #(...)
  features:
    oomKill:
      enabled: true
```

**Note**: When using COS (Container Optimized OS), override the `src` volume in the node Agent:
```yaml
apiVersion: datadoghq.com/v2alpha1
kind: DatadogAgent
metadata:
  name: datadog
spec:
  #(...)
  features:
    oomKill:
      enabled: true
  override:
    nodeAgent:
      volumes:
      - emptyDir: {}
        name: src
```

##### Helm
With the [Datadog Helm chart][4], set the following configuration in your `values.yaml` file:

```yaml
datadog:
  #(...)
  systemProbe:
    enableOOMKill: true
```

With these settings, the `system-probe` container is automatically deployed with the required configuration and permissions.

<!-- xxz tab xxx -->

<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][5] and look for `oom_kill` under the `Collector` section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Service Checks

The OOM Kill check does not include any service checks.

### Events

The OOM Kill check submits an event for each OOM Kill that includes the killed process ID and name, as well as the triggering process ID and name.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: /account/settings/agent/latest
[2]: https://github.com/DataDog/datadog-agent/blob/main/cmd/agent/dist/conf.d/oom_kill.d/conf.yaml.default
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[4]: https://github.com/DataDog/helm-charts
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/oom_kill/metadata.csv
[7]: https://docs.datadoghq.com/help/
