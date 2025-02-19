# Agent Check: GPU

## Overview

This check monitors GPU devices and their utilization through the Datadog Agent.

Supported vendors: NVIDIA.

- Track utilization of GPU devices and retrieve performance and health metrics.
- Monitor processes that are using GPU devices and their performance.

## Setup

### Installation

The GPU check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

The check also uses eBPF probes to assign GPU usage and performance metrics to processes. eBPF programs are loaded by the `system-probe` component.

**Note**: The `system-probe` GPU component (which generates per-process metrics) requires Linux kernel 5.8 or later. Windows is not supported.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

Enabling the `gpu` integration requires `system-probe` to have the configuration option enabled.  Inside the `system-probe.yaml` configuration file, the following parameters must be set:

```yaml
gpu_monitoring:
  enabled: true
```

The check in the Agent configuration file is enabled by default whenever NVIDIA GPUs and their drivers are detected in the system. However, it can also be configured manually following these steps:

1. Edit the `gpu.d/conf.yaml` file, in the `conf.d/` folder at the root of your
   Agent's configuration directory, to start collecting your GPU performance data.
   See the [sample gpu.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4].

This check is automatically enabled when the Agent is running on a host with NVIDIA GPUs and the NVIDIA drivers and libraries installed.

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Important: Running on Helm/Kubernetes in mixed environments

One important thing to note in the deployment for Kubernetes clusters is that, in order to access the GPUs, the Datadog Agent pods needs access to both the GPUs and NVIDIA's NVML library (`libnvidia-ml.so`). Due to the design of NVIDIA's Kubernetes Device Plugin, in order to have access to those features the Agent pods will need to run with the `nvidia` runtime class. This means that the Agent pods will not be able to run in the default runtime class.

This can cause issues in clusters where some nodes have GPUs and others don't: if we deploy with a single runtime class, the Agent will only run on a subset of the cluster nodes. Both the Helm and Datadog Operator deployments can be configured to deploy in this situation correctly to both types of nodes, but it requires some additional configuration as described below.

#### Helm

For Helm configurations where all the nodes have GPUs, you can set up the Datadog Agent to monitor GPUs by defining the `gpuMonitoring` parameter in the `values.yaml` file.

```yaml
datadog:
  gpuMonitoring:
    enabled: true
```

For **mixed environments**, two different Helm charts need to be deployed with different affinity sets and with one of them joining the other's Cluster Agent [as documented here](https://github.com/DataDog/helm-charts/tree/main/charts/datadog#how-to-join-a-cluster-agent-from-another-helm-chart-deployment-linux).

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

The `nvidia.com/gpu.present` tag is used above as it's automatically added to GPU nodes by the NVIDIA GPU operator. However, any other appropriate tag may be chosen.

2. Create another file (for example, `values-gpu.yaml`) to apply on top of the previous one. In this file, enable GPU monitoring, configure the Cluster Agent to join the existing cluster as per the [instructions],(<https://github.com/DataDog/helm-charts/tree/main/charts/datadog#how-to-join-a-cluster-agent-from-another-helm-chart-deployment-linux>) and include the affinity for the GPU nodes:

```yaml
# GPU-specific values-gpu.yaml (for GPU nodes)
datadog:
  kubeStateMetricsEnabled: false # Disabled as we're joining an existing Cluster Agent
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
```

For **mixed environments**, use the [DatadogAgentProfiles feature](https://github.com/DataDog/datadog-operator/blob/main/docs/datadog_agent_profiles.md) of the operator, which allows different configurations to be deployed for different nodes. In this case, it is not necessary to modify the DatadogAgent manifest. Instead, create a profile that enables the configuration on GPU nodes only:

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

[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://github.com/DataDog/datadog-agent/blob/main/cmd/agent/dist/conf.d/gpu.d/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/gpu/metadata.csv
[8]: https://docs.datadoghq.com/help/
