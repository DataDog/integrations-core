# Agent Check: Containerd

## Overview

This check monitors the Containerd container runtime.

## Setup

### Installation

Containerd is a core [Datadog Agent][1] check. You must configure Containerd in both `datadog.yaml` and `containerd.d/conf.yaml`.

In `datadog.yaml`, configure your `cri_socket_path` for the Agent to query Containerd. In `containerd.d/conf.yaml`, configure the check instance settings (such as `filters`) for the events.

#### Installation on containers

If you are using the Agent in a container, setting the `DD_CRI_SOCKET_PATH` environment variable to the Containerd socket automatically enables the Containerd integration with the default configuration.

For example, to install the integration on Kubernetes, edit your DaemonSet to mount the Containerd socket from the host node to the Agent container and set the `DD_CRI_SOCKET_PATH` environment variable to the DaemonSet mount path:

<!-- xxx tabs xxx -->
<!-- xxx tab "Linux container" xxx -->

##### Linux container

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

<!-- xxz tab xxx -->
<!-- xxx tab "Windows Container" xxx -->

##### Windows container

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
              value: \\\\.\\pipe\\containerd-containerd
          volumes:
            - hostPath:
                path: \\\\.\\pipe\\containerd-containerd
              name: containerdsocket
          volumeMounts:
            - name: containerdsocket
              mountPath: \\\\.\\pipe\\containerd-containerd
```

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Configuration

1. Edit the `containerd.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Containerd performance data. See the [sample containerd.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3]

### Validation

[Run the Agent's `status` subcommand][4] and look for `containerd` under the Checks section.

## Data Collected

### Metrics

Containerd collects metrics about the resource usage of your containers.

CPU, memory, block I/O, or huge page table metrics are collected out of the box. Additionally, you can also collect some disk metrics.

See [metadata.csv][5] for a list of metrics provided by this integration.

This integration works on Linux and Windows, but some metrics are OS dependent. Look at `metadata.csv` for the list of OS dependent metrics. 
 
### Events

The Containerd check can collect events. Use `filters` to select the relevant events. See the [sample containerd.d/conf.yaml][2] to have more details.

### Service Checks

See [service_checks.json][6] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][3].


[1]: https://app.datadoghq.com/account/settings/agent/latest
[2]: https://github.com/DataDog/datadog-agent/blob/master/cmd/agent/dist/conf.d/containerd.d/conf.yaml.default
[3]: https://docs.datadoghq.com/help/
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://github.com/DataDog/integrations-core/blob/master/containerd/metadata.csv
[6]: https://github.com/DataDog/integrations-core/blob/master/containerd/assets/service_checks.json
