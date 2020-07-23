# Agent Check: Containerd

## Overview

This Check monitors the Container Runtime Containerd.

## Setup

### Installation

Containerd is a core Agent 6 check and thus needs to be configured in both in `datadog.yaml` and with `containerd.d/conf.yaml`.

In `datadog.yaml`, configure your `cri_socket_path` for the Agent to query Containerd. In `containerd.d/conf.yaml`, configure the Check instance settings (such as `filters`) for the events.

#### Installation on containers

If you are using the Agent in a container, setting the `DD_CRI_SOCKET_PATH` environment variable to the Containerd socket automatically enables the `Containerd` integration with the default configuration.

For example, to install the integration on Kubernetes, edit your daemonset to mount the Containerd socket from the host node to the Agent container and set the `DD_CRI_SOCKET_PATH` env var to the daemonset mountPath:

```yaml
apiVersion: extensions/v1beta1
kind: DaemonSet
metadata:
  name: datadog-agent
spec:
  template:
    spec:
      containers:
        - name: datadog-agent
          # ...
          env:
            - name: DD_CRI_SOCKET_PATH
              value: /var/run/containerd/containerd.sock
          volumeMounts:
            - name: containerdsocket
              mountPath: /var/run/containerd/containerd.sock
            - mountPath: /host/var/run
              name: var-run
              readOnly: true
          volumes:
            - hostPath:
                path: /var/run/containerd/containerd.sock
              name: containerdsocket
            - hostPath:
                path: /var/run
              name: var-run
```

**Note:** The `/var/run` directory must be mounted from the host to run the integration without issues.

### Configuration

1. Edit the `containerd.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Containerd performance data. See the [sample containerd.d/conf.yaml][1] for all available configuration options.

2. [Restart the Agent][2]

### Validation

[Run the Agent's `status` subcommand][3] and look for `containerd` under the Checks section.

## Data Collected

### Metrics

Containerd collects metrics about the resource usage of your containers.

CPU, memory, block I/O, or huge page table metrics are collected out of the box. Additionally, you can also collect some disk metrics.

See [metadata.csv][4] for a list of metrics provided by this Integration.

### Service Checks

Containerd includes a Service Check `containerd.health` to notify on the health of the connection to the Containerd Socket.

### Events

The Containerd Check can collect events. Use `filters` to select the relevant events. Refer to the [sample containerd.d/conf.yaml][1] to have more details.

## Troubleshooting

Need help? Contact [Datadog support][2].

[1]: https://github.com/DataDog/datadog-agent/blob/master/cmd/agent/dist/conf.d/containerd.d/conf.yaml.example
[2]: https://docs.datadoghq.com/help/
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[4]: https://github.com/DataDog/integrations-core/blob/master/containerd/metadata.csv
