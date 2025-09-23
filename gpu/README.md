# Agent Check: GPU

## Overview

This check monitors GPU devices and their utilization through the Datadog Agent.

Supported vendors: NVIDIA.

- Track utilization of GPU devices and retrieve performance and health metrics.
- Monitor processes that are using GPU devices and their performance.

## Requirements

- NVIDIA driver version: 450.51 and above
- Datadog agent version: latest
- Supported OS: Linux only
- Linux kernel version: 5.8 and above

## Setup

### Installation

The GPU check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

The check also uses eBPF probes to assign GPU usage and performance metrics to processes. eBPF programs are loaded by the `system-probe` component.

**Note**: The `system-probe` GPU component (which generates per-process metrics) requires Linux kernel 5.8 or later. Windows is not supported.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

The agent needs to be configured to enable GPU-related features. Add the following parameters to the `/etc/datadog-agent/datadog.yaml` configuration file and then restart the Agent:

```yaml
collect_gpu_tags: true
enable_nvml_detection: true
```

Enabling the `gpu` integration requires `system-probe` to have the configuration option enabled for collecting per-process metrics. Inside the `/etc/datadog-agent/system-probe.yaml` configuration file, the following parameters must be set:

```yaml
gpu_monitoring:
  enabled: true
```

The check in the Agent configuration file is enabled by default whenever NVIDIA GPUs and their drivers are detected in the system, as long as the `enable_nvml_detection` parameter is set to `true`. However, it can also be configured manually following these steps:

1. Edit the `gpu.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory, to start collecting your GPU performance data.
   See the [sample gpu.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4].

This check is automatically enabled when the Agent is running on a host with NVIDIA GPUs and the NVIDIA drivers and libraries installed.

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Docker

The GPU monitoring feature requires the `system-probe` component to be enabled, so in addition to the configuration above for the `datadog.yaml` and `system-probe.yaml` files, the following needs to be added to the `docker run` command:

```bash
docker run --cgroupns host \
  --pid host \
  -e DD_API_KEY="<DATADOG_API_KEY>" \
  -e DD_GPU_MONITORING_ENABLED=true \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /proc/:/host/proc/:ro \
  -v /sys/fs/cgroup/:/host/sys/fs/cgroup:ro \
  -v /sys/kernel/debug:/sys/kernel/debug \
  -v /lib/modules:/lib/modules:ro \
  -v /usr/src:/usr/src:ro \
  -v /var/tmp/datadog-agent/system-probe/build:/var/tmp/datadog-agent/system-probe/build \
  -v /var/tmp/datadog-agent/system-probe/kernel-headers:/var/tmp/datadog-agent/system-probe/kernel-headers \
  -v /etc/apt:/host/etc/apt:ro \
  -v /etc/yum.repos.d:/host/etc/yum.repos.d:ro \
  -v /etc/zypp:/host/etc/zypp:ro \
  -v /etc/pki:/host/etc/pki:ro \
  -v /etc/yum/vars:/host/etc/yum/vars:ro \
  -v /etc/dnf/vars:/host/etc/dnf/vars:ro \
  -v /etc/rhsm:/host/etc/rhsm:ro \
  -e HOST_ROOT=/host/root \
  --security-opt apparmor:unconfined \
  --cap-add=SYS_ADMIN \
  --cap-add=SYS_RESOURCE \
  --cap-add=SYS_PTRACE \
  --cap-add=NET_ADMIN \
  --cap-add=NET_BROADCAST \
  --cap-add=NET_RAW \
  --cap-add=IPC_LOCK \
  --cap-add=CHOWN \
  gcr.io/datadoghq/agent:latest
```

#### Important: Running on Helm/Kubernetes in mixed environments

One important thing to note in the deployment for Kubernetes clusters is that, in order to access the GPUs, the Datadog Agent pods needs access to both the GPUs and NVIDIA's NVML library (`libnvidia-ml.so`). Due to the design of NVIDIA's Kubernetes Device Plugin, in order to have access to those features the Agent pods will need to run with the `nvidia` runtime class. This means that the Agent pods will not be able to run in the default runtime class.

This can cause issues in clusters where some nodes have GPUs and others don't: if we deploy with a single runtime class, the Agent will only run on a subset of the cluster nodes. Both the Helm and Datadog Operator deployments can be configured to deploy in this situation correctly to both types of nodes, but it requires some additional configuration as described below.

#### Helm

For Helm configurations where all the nodes have GPUs, you can set up the Datadog Agent to monitor GPUs by defining the `gpuMonitoring` parameter in the `values.yaml` file.

```yaml
datadog:
  enable_nvml_detection: true
  collect_gpu_tags: true
  gpuMonitoring:
    enabled: true
```

For **mixed environments**, two different Helm charts need to be deployed with different affinity sets and with one of them joining the other's Cluster Agent [as documented here](https://github.com/DataDog/helm-charts/tree/main/charts/datadog#how-to-join-a-cluster-agent-from-another-helm-chart-deployment-linux).

While the `nvidia.com/gpu.present` tag is commonly used to identify GPU nodes (often automatically added by the NVIDIA GPU operator), your specific environment might use different tags or labeling schemes. It's important to identify the correct tag and value that distinguishes your GPU nodes from non-GPU nodes. You can then adapt the examples below accordingly.

Assuming we have already a `values.yml` file for a regular, non-GPU deployment, the steps to enable GPU monitoring only on GPU nodes are the following:

1. In `agents.affinity`, add a node selector that stops the non-GPU Agent from running on GPU nodes:

```yaml
# Base values.yaml (for non-GPU nodes)
agents:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: nvidia.com/gpu.present
            operator: NotIn
            values:
              - "true"
```

Additionally, if you need to select nodes based on the presence of a label key, irrespective of its value, you can use the `Exists` [operator](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/#node-affinity). Conversely, to exclude nodes that have a specific label key, you can use `DoesNotExist`. For example, to select nodes that have the label `custom.gpu/available` (regardless of its value), you would use `operator: Exists`.

2. Create another file (for example, `values-gpu.yaml`) to apply on top of the previous one. In this file, enable GPU monitoring, configure the Cluster Agent to join the existing cluster as per the [instructions],(<https://github.com/DataDog/helm-charts/tree/main/charts/datadog#how-to-join-a-cluster-agent-from-another-helm-chart-deployment-linux>) and include the affinity for the GPU nodes:

```yaml
# GPU-specific values-gpu.yaml (for GPU nodes)
datadog:
  kubeStateMetricsEnabled: false # Disabled as we're joining an existing Cluster Agent
  enable_nvml_detection: true
  collect_gpu_tags: true
  gpuMonitoring:
    enabled: true

agents:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: nvidia.com/gpu.present
            operator: In
            values:
              - "true"

existingClusterAgent:
  join: true

# Disabled datadogMetrics deployment since it should have been already deployed with the other chart release.
datadog-crds:
  crds:
    datadogMetrics: false
```

3. Deploy the datadog chart twice, first with the first `values.yaml` file as modified in step 1, and then a second time (with a different name) adding the `values-gpu.yaml` file as defined in step 2:

```bash
helm install -f values.yaml datadog datadog
helm install -f values.yaml -f values-gpu.yaml datadog-gpu datadog
```

#### Datadog Operator

_**Minimum required operator version: 1.14**_

To enable the GPU feature in clusters where all the nodes have GPUs, set the `features.gpu.enabled` parameter in the DatadogAgent manifest:

```yaml
apiVersion: datadoghq.com/v2alpha1
kind: DatadogAgent
metadata:
  name: datadog
spec:
  features:
    gpu:
      enabled: true
  # For operator versions below 1.18, add this section
  override:
    nodeAgent:
     volumes:
        # Add this volume for operator version below 1.18, unless other system-probe features
        # such as npm, cws, usm or oom_kill are enabled.
        - name: debugfs
          hostPath:
            path: /sys/kernel/debug
      containers:
        agent:
          env:
            # add this env var, if using operator version 1.14.x
            - name: DD_ENABLE_NVML_DETECTION
              value: "true"
            # add this env var, if using operator versions 1.14.x or 1.15.x
            - name: DD_COLLECT_GPU_TAGS
              value: "true"
        system-probe:
          volumeMounts:
            # Add this volume for operator version below 1.18, unless other system-probe features
            # such as Cloud Network Monitoring, Cloud Workload Security or Universal Service Monitoring
            # are enabled.
            - name: debugfs
              mountPath: /sys/kernel/debug
```

For **mixed environments**, use the [DatadogAgentProfiles (DAP) feature](https://github.com/DataDog/datadog-operator/blob/main/docs/datadog_agent_profiles.md) of the operator, which allows different configurations to be deployed for different nodes. Note that this feature is disabled by default, so it needs to be enabled. For more information, see [Enabling DatadogAgentProfiles](https://github.com/DataDog/datadog-operator/blob/main/docs/datadog_agent_profiles.md#enabling-datadogagentprofiles).

Modifying the DatadogAgent manifest is necessary to enable certain features that are not supported by the DAP yet:
- In the existing configuration, enable the `system-probe` container in the datadog-agent pods. Because the DAP feature does not yet support conditionally enabling containers, a feature that uses `system-probe` needs to be enabled for all Agent pods.
  - You can check this by looking at the list of containers when running `kubectl describe pod <datadog-agent-pod-name> -n <namespace>`.
  - Datadog recommends enabling the `oomKill` integration, as it is lightweight and does not require any additional configuration or cost.
- Configure the Agent so that the NVIDIA container runtime exposes GPUs to the Agent.
  - You can do this using environment variables or volume mounts, depending on whether the `accept-nvidia-visible-devices-as-volume-mounts` parameter is set to `true` or `false` in the NVIDIA container runtime configuration.
  - Datadog recommends configuring the Agent both ways, as it reduces the chance of misconfiguration. There are no side effects to having both.
- Expose the PodResources socket to the Agent to integrate with the Kubernetes Device Plugin.
  - This needs to be done globally, as the DAP does not yet support conditional volume mounts.

In summary, the changes that need to be applied to the DatadogAgent manifest are the following:

```yaml
spec:
  features:
    oomKill:
      # Only enable this feature if there is nothing else that requires the system-probe container in all Agent pods
      # Examples of system-probe features are npm, cws, usm
      enabled: true

override:
    nodeAgent:
      volumes:
        - name: nvidia-devices
          hostPath:
            path: /dev/null
        - name: pod-resources
          hostPath:
            path: /var/lib/kubelet/pod-resources
      containers:
        agent:
          env:
            - name: NVIDIA_VISIBLE_DEVICES
              value: "all"
          volumeMounts:
            - name: nvidia-devices
              mountPath: /dev/nvidia-visible-devices
            - name: pod-resources
              mountPath: /var/lib/kubelet/pod-resources
        system-probe:
          env:
            - name: NVIDIA_VISIBLE_DEVICES
              value: "all"
          volumeMounts:
            - name: nvidia-devices
              mountPath: /dev/nvidia-visible-devices
            - name: pod-resources
              mountPath: /var/lib/kubelet/pod-resources
```

Once the DatadogAgent configuration is changed, create a profile that enables the GPU feature configuration on GPU nodes only:

```yaml
apiVersion: datadoghq.com/v1alpha1
kind: DatadogAgentProfile
metadata:
  name: gpu-nodes
spec:
  profileAffinity:
    profileNodeAffinity:
      - key: nvidia.com/gpu.present
        operator: In
        values:
          - "true"
  config:
    override:
      nodeAgent:
        runtimeClassName: nvidia
        containers:
          system-probe:
            env:
              - name: DD_GPU_MONITORING_ENABLED
                value: "true"
          agent:
            env:
              - name: DD_ENABLE_NVML_DETECTION
                value: "true"
              - name: DD_COLLECT_GPU_TAGS
                value: "true"
```

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][5] and look for `gpu` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Events

The GPU check does not include any events.

### Service Checks

The GPU check does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][8].

[2]: /account/settings/agent/latest
[3]: https://github.com/DataDog/datadog-agent/blob/main/cmd/agent/dist/conf.d/gpu.d/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/gpu/metadata.csv
[8]: https://docs.datadoghq.com/help/
