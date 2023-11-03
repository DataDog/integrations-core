# Agent Check: DCGM Exporter

## Overview

This check submits metrics exposed by the [NVIDIA DCGM Exporter][16] in Datadog Agent format. For more information on NVIDIA Data Center GPU Manager (DCGM), see [NVIDIA DCGM][15].

## Setup

### Installation

Starting from Agent release 7.47.0, the DCGM check is included in the [Datadog Agent][1] package. However, you need to spin up the DCGM Exporter container to expose the GPU metrics in order for the Agent to collect this data. As the default counters are not sufficient, Datadog recommends using the following DCGM configuration to cover the same ground as the NVML integration in addition to having useful metrics.

```
# Format
# If line starts with a '#' it is considered a comment
# DCGM FIELD                                                      ,Prometheus metric type ,help message

# Clocks
DCGM_FI_DEV_SM_CLOCK                                              ,gauge                  ,SM clock frequency (in MHz).
DCGM_FI_DEV_MEM_CLOCK                                             ,gauge                  ,Memory clock frequency (in MHz).

# Temperature
DCGM_FI_DEV_MEMORY_TEMP                                           ,gauge                  ,Memory temperature (in C).
DCGM_FI_DEV_GPU_TEMP                                              ,gauge                  ,GPU temperature (in C).

# Power
DCGM_FI_DEV_POWER_USAGE                                           ,gauge                  ,Power draw (in W).
DCGM_FI_DEV_TOTAL_ENERGY_CONSUMPTION                              ,counter                ,Total energy consumption since boot (in mJ).

# PCIE
DCGM_FI_DEV_PCIE_REPLAY_COUNTER                                   ,counter                ,Total number of PCIe retries.

# Utilization (the sample period varies depending on the product)
DCGM_FI_DEV_GPU_UTIL                                              ,gauge                  ,GPU utilization (in %).
DCGM_FI_DEV_MEM_COPY_UTIL                                         ,gauge                  ,Memory utilization (in %).
DCGM_FI_DEV_ENC_UTIL                                              ,gauge                  ,Encoder utilization (in %).
DCGM_FI_DEV_DEC_UTIL                                              ,gauge                  ,Decoder utilization (in %).

# Errors and violations
DCGM_FI_DEV_XID_ERRORS                                            ,gauge                  ,Value of the last XID error encountered.

# Memory usage
DCGM_FI_DEV_FB_FREE                                               ,gauge                  ,Framebuffer memory free (in MiB).
DCGM_FI_DEV_FB_USED                                               ,gauge                  ,Framebuffer memory used (in MiB).

# NVLink
DCGM_FI_DEV_NVLINK_BANDWIDTH_TOTAL                                ,counter                ,Total number of NVLink bandwidth counters for all lanes.

# VGPU License status
DCGM_FI_DEV_VGPU_LICENSE_STATUS                                   ,gauge                  ,vGPU License status

# Remapped rows
DCGM_FI_DEV_UNCORRECTABLE_REMAPPED_ROWS                           ,counter                ,Number of remapped rows for uncorrectable errors
DCGM_FI_DEV_CORRECTABLE_REMAPPED_ROWS                             ,counter                ,Number of remapped rows for correctable errors
DCGM_FI_DEV_ROW_REMAP_FAILURE                                     ,gauge                  ,Whether remapping of rows has failed

# DCP metrics
DCGM_FI_PROF_PCIE_TX_BYTES                                        ,counter                ,The number of bytes of active pcie tx data including both header and payload.
DCGM_FI_PROF_PCIE_RX_BYTES                                        ,counter                ,The number of bytes of active pcie rx data including both header and payload.
DCGM_FI_PROF_GR_ENGINE_ACTIVE                                     ,gauge                  ,Ratio of time the graphics engine is active (in %).
DCGM_FI_PROF_SM_ACTIVE                                            ,gauge                  ,The ratio of cycles an SM has at least 1 warp assigned (in %).
DCGM_FI_PROF_SM_OCCUPANCY                                         ,gauge                  ,The ratio of number of warps resident on an SM (in %).
DCGM_FI_PROF_PIPE_TENSOR_ACTIVE                                   ,gauge                  ,Ratio of cycles the tensor (HMMA) pipe is active (in %).
DCGM_FI_PROF_DRAM_ACTIVE                                          ,gauge                  ,Ratio of cycles the device memory interface is active sending or receiving data (in %).
DCGM_FI_PROF_PIPE_FP64_ACTIVE                                     ,gauge                  ,Ratio of cycles the fp64 pipes are active (in %).
DCGM_FI_PROF_PIPE_FP32_ACTIVE                                     ,gauge                  ,Ratio of cycles the fp32 pipes are active (in %).
DCGM_FI_PROF_PIPE_FP16_ACTIVE                                     ,gauge                  ,Ratio of cycles the fp16 pipes are active (in %).

# Datadog additional recommended fields
DCGM_FI_DEV_COUNT                                                 ,counter                ,Number of Devices on the node.
DCGM_FI_DEV_FAN_SPEED                                             ,gauge                  ,Fan speed for the device in percent 0-100.
DCGM_FI_DEV_SLOWDOWN_TEMP                                         ,gauge                  ,Slowdown temperature for the device.
DCGM_FI_DEV_POWER_MGMT_LIMIT                                      ,gauge                  ,Current power limit for the device.
DCGM_FI_DEV_PSTATE                                                ,gauge                  ,Performance state (P-State) 0-15. 0=highest
DCGM_FI_DEV_FB_TOTAL                                              ,gauge                  ,
DCGM_FI_DEV_FB_RESERVED                                           ,gauge                  ,
DCGM_FI_DEV_FB_USED_PERCENT                                       ,gauge                  ,
DCGM_FI_DEV_CLOCK_THROTTLE_REASONS                                ,gauge                  ,Current clock throttle reasons (bitmask of DCGM_CLOCKS_THROTTLE_REASON_*)

DCGM_FI_PROCESS_NAME                                              ,label                  ,The Process Name.
DCGM_FI_CUDA_DRIVER_VERSION                                       ,label                  ,
DCGM_FI_DEV_NAME                                                  ,label                  ,
DCGM_FI_DEV_MINOR_NUMBER                                          ,label                  ,
DCGM_FI_DRIVER_VERSION                                            ,label                  ,
DCGM_FI_DEV_BRAND                                                 ,label                  ,
DCGM_FI_DEV_SERIAL                                                ,label                  ,
```


<!-- xxx tabs xxx -->
<!-- xxx tab "Host | Docker" xxx -->

#### Docker

To configure the exporter in a Docker environment:

1. Create the file `$PWD/default-counters.csv` which contains the default fields from NVIDIA `etc/default-counters.csv` as well as additional Datadog-recommended fields. To add more fields for collection, follow [these instructions][9]. For the complete list of fields, see the [DCGM API reference manual][10].
2. Run the Docker container using the following command:
   ```shell
   sudo docker run --pid=host --privileged -e DCGM_EXPORTER_INTERVAL=3 --gpus all -d -v /proc:/proc -v $PWD/default-counters.csv:/etc/dcgm-exporter/default-counters.csv -p 9400:9400 --name dcgm-exporter nvcr.io/nvidia/k8s/dcgm-exporter:3.1.7-3.1.4-ubuntu20.04
   ```

<!-- xxz tab xxx -->
<!-- xxx tab "Kubernetes" xxx -->

#### Kubernetes (DCGM exporter Helm chart)

The DCGM exporter can quickly be installed in a Kubernetes environment using the NVIDIA DCGM Exporter Helm chart. The instructions below are derived from the template provided by NVIDIA [here](https://github.com/NVIDIA/dcgm-exporter#quickstart-on-kubernetes).

1. Add the NVIDIA DCGM Exporter Helm repository and ensure it is up-to-date :
   ```shell
   helm repo add gpu-helm-charts https://nvidia.github.io/dcgm-exporter/helm-charts && helm repo update
   ```
2. Create a `ConfigMap` containing the Datadog-recommended metrics from [Installation](#Installation), as well as the `RoleBinding` and `Role` used by the DCGM pods to retrieve the `ConfigMap` using the manifest below :
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     name: dcgm-exporter-read-datadog-cm
     namespace: default
   rules:
   - apiGroups: [""]
     resources: ["configmaps"]
     resourceNames: ["datadog-dcgm-exporter-configmap"]
     verbs: ["get"]
   ---
   apiVersion: rbac.authorization.k8s.io/v1
   kind: RoleBinding
   metadata:
     name: dcgm-exporter-datadog
     namespace: default
   subjects:
   - kind: ServiceAccount
     name: dcgm-datadog-dcgm-exporter
     namespace: default
   roleRef:
     kind: Role 
     name: dcgm-exporter-read-datadog-cm
     apiGroup: rbac.authorization.k8s.io
   ---
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: datadog-dcgm-exporter-configmap
     namespace: default
   data:
     metrics: |
         # Copy the content from the Installation section.
   ```
3. Create your DCGM Exporter Helm chart `dcgm-values.yaml` with the following content : 
   ```yaml
   # Exposing more metrics than the default for additional monitoring - this requires the use of a dedicated ConfigMap for which the Kubernetes ServiceAccount used by the exporter has access thanks to step 1.
   # Ref: https://github.com/NVIDIA/dcgm-exporter/blob/e55ec750def325f9f1fdbd0a6f98c932672002e4/deployment/values.yaml#L38
   arguments: ["-m", "default:datadog-dcgm-exporter-configmap"]

   # Datadog Autodiscovery V2 annotations
   podAnnotations:
     ad.datadoghq.com/exporter.checks: |-
       {
         "dcgm": {
           "instances": [
             {
               "openmetrics_endpoint": "http://%%host%%:9400/metrics"
             }
           ]
         }
       }
   # Optional - Disabling the ServiceMonitor which requires Prometheus CRD - can be re-enabled if Prometheus CRDs are installed in your cluster
   serviceMonitor:
     enabled: false
   ```
4. Install the DCGM Exporter Helm chart in the `default` namespace with the following command, while being in the directory with your `dcgm-values.yaml` :
   ```shell
   helm install dcgm-datadog gpu-helm-charts/dcgm-exporter -n default -f dcgm-values.yaml
   ```

**Note**: You can modify the release name `dcgm-datadog` as well as the namespace, but you must modify accordingly the manifest from step 1.

<!-- xxz tab xxx -->
<!-- xxx tab "Operator" xxx -->

#### Kubernetes (NVIDIA GPU Operator)

The DCGM exporter can be installed in a Kubernetes environment by using NVIDIA GPU Operator. The instructions below are derived from the template provided by NVIDIA [here](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/getting-started.html).

1. Add the NVIDIA GPU Operator Helm repository and ensure it is up-to-date :
   ```shell
   helm repo add nvidia https://helm.ngc.nvidia.com/nvidia && helm repo update
   ```
2. Follow the [Custom Metrics Config](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/getting-started.html#custom-metrics-config) instructions with the CSV from [Installation](#installation) :
    * Fetch the metrics file and save as `dcgm-metrics.csv`: `curl https://raw.githubusercontent.com/NVIDIA/dcgm-exporter/main/etc/dcp-metrics-included.csv > dcgm-metrics.csv`
    * Edit the metrics file by replacing its content with the Datadog-provided mapping.
    * Create a namespace `gpu-operator` if one is not already present: `kubectl create namespace gpu-operator`.
    * Create a ConfigMap using the file edited above: `kubectl create configmap metrics-config -n gpu-operator --from-file=dcgm-metrics.csv`
3. Create your GPU Operator Helm chart `dcgm-values.yaml` with the following content: 
   ```yaml
   # Refer to NVIDIA documentation for the driver and toolkit for your GPU-enabled nodes - example below for Amazon Linux 2 g5.xlarge
   driver:
     enabled: true
   toolkit:
     version: v1.13.5-centos7
   # Using custom metrics configuration to collect recommended Datadog additional metrics - requires the creation of the metrics-config ConfigMap from the previous step
   # Ref: https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/getting-started.html#custom-metrics-config
   dcgmExporter:
     config:
       name: metrics-config
     env:
     - name: DCGM_EXPORTER_COLLECTORS
       value: /etc/dcgm-exporter/dcgm-metrics.csv
   # Adding Datadog autodiscovery V2 annotations
   daemonsets:
     annotations:
       ad.datadoghq.com/nvidia-dcgm-exporter.checks: |-
         {
           "dcgm": {
             "instances": [
               {
                 "openmetrics_endpoint": "http://%%host%%:9400/metrics"
               }
             ]
           }
         }
   ```
4. Install the DCGM Exporter Helm chart in the `default` namespace with the following command, while being in the directory with your `dcgm-values.yaml`:
   ```bash
   helm install datadog-dcgm-gpu-operator -n gpu-operator nvidia/gpu-operator -f dcgm-values.yaml
   ```

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->


### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

##### Metric collection

1. Edit the `dcgm.d/conf.yaml` file (located in the `conf.d/` folder at the root of your Agent's configuration directory) to start collecting your GPU Metrics. See the [sample dcgm.d/conf.yaml][3] for all available configuration options.

   ```
   instances:

      ## @param openmetrics_endpoint - string - required
      ## The URL exposing metrics in the OpenMetrics format.
      ##
      ## Set this to <listenAddress>/<handlerPath> as configured in your DCGM Server
      #
      - openmetrics_endpoint: http://localhost:9400/metrics
   ```

Use the `extra_metrics` configuration field to add metrics that go beyond the ones Datadog [supports out of the box][6]. See the [NVIDIA docs][10] for the full list of metrics that dcgm-exporter can collect. Make sure to [enable these fields in the dcgm-exporter configuration][9] as well.

<!-- xxz tab xxx -->
<!-- xxx tab "Docker" xxx -->

#### Docker

##### Metric collection

Set [Autodiscovery Integrations Templates][5] as Docker labels on your DCGM exporter container:

```yaml
LABEL "com.datadoghq.ad.check_names"='["dcgm"]'
LABEL "com.datadoghq.ad.init_configs"='[{}]'
LABEL "com.datadoghq.ad.instances"='[{"openmetrics_endpoint": "http://%%host%%:9400/metrics"}]'
```

<!-- xxz tab xxx -->
<!-- xxx tab "Kubernetes" xxx -->

#### Kubernetes

**Note**: If you followed the instructions for the [DCGM Exporter Helm chart](#kubernetes-dcgm-exporter-helm-chart) or [GPU Operator](#kubernetes-nvidia-gpu-operator), the annotations are already applied to the pods and the instructions below can be ignored.

1. To configure this check for an Agent running on Kubernetes:

##### Metric collection

Set [Autodiscovery Integrations Templates][12] as pod annotations on your application container. Aside from this, templates can also be configured with [a file, a configmap, or a key-value store][11].

**Annotations v2** (for Datadog Agent v7.47+)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: '<POD_NAME>'
  annotations:
    ad.datadoghq.com/dcgm.checks: |
      {
        "dcgm": {
          "init_config": {},
          "instances": [
            {
              "openmetrics_endpoint": "http://%%host%%:9400/metrics"
            }
          ]
        }
      }
spec:
  containers:
    - name: dcgm
```

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

When you're finished making configuration changes, [restart the Agent][4].

### Validation

[Run the Agent's status subcommand][5] and look for `dcgm` under the Checks section.


### Adjusting Monitors

The out-of-the-box monitors that come with this integration have some default values based on their alert thresholds. For example, the GPU temperature is determined based on an [acceptable range for industrial devices][13].
However, Datadog recommends that you check to make sure these values suit your particular needs.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics that this integration provides.

### Events

The DCGM integration does not include any events.

### Service Checks

See [service_checks.json][7] for a list of service checks that this integration provides.

## Troubleshooting

### Metric Mapping

If you have added some metrics that don't appear in the [metadata.csv][6] above but appear in your account with the format `DCGM_FI_DEV_NEW_METRIC`, remap these metrics in the [dcgm.d/conf.yaml][3] configuration file:
```yaml
    ## @param extra_metrics - (list of string or mapping) - optional
    ## This list defines metrics to collect from the `openmetrics_endpoint`, in addition to
    ## what the check collects by default. If the check already collects a metric, then
    ## metric definitions here take precedence. Metrics may be defined in 3 ways:
    ...
```
The example below appends the part in `NEW_METRIC` to the namespace (`dcgm.`), giving `dcgm.new_metric`:

```yaml
    extra_metrics:
    - DCGM_FI_DEV_NEW_METRIC: new_metric
```

### DCGM field is enabled but not being submitted?

If a field is not being collected even after enabling it in `default-counters.csv` and performing a `curl` request to `host:9400/metrics`, the [dcgm-exporter developers recommend][14] looking at the log file at `var/log/nv-hostengine.log`.

**Note:** The `dcgm-exporter` is a thin wrapper around lower-level libraries and drivers which do the actual reporting.

### Increased Resource Consumption

In some cases, the `DCGM_FI_DEV_GPU_UTIL` metric can cause heavier resource consumption. If you're experiencing this issue:

1. Disable `DCGM_FI_DEV_GPU_UTIL` in `default-counters.csv`.
2. Make sure the following fields are enabled in `default-counters.csv`:
   - `DCGM_FI_PROF_DRAM_ACTIVE`
   - `DCGM_FI_PROF_GR_ENGINE_ACTIVE`
   - `DCGM_FI_PROF_PCIE_RX_BYTES`
   - `DCGM_FI_PROF_PCIE_TX_BYTES`
   - `DCGM_FI_PROF_PIPE_FP16_ACTIVE`
   - `DCGM_FI_PROF_PIPE_FP32_ACTIVE`
   - `DCGM_FI_PROF_PIPE_FP64_ACTIVE`
   - `DCGM_FI_PROF_PIPE_TENSOR_ACTIVE`
   - `DCGM_FI_PROF_SM_ACTIVE`
   - `DCGM_FI_PROF_SM_OCCUPANCY`
3. Restart both dcgm-exporter and the Datadog Agent.

### Need help?

Contact [Datadog support][8].

## Further Reading

Additional helpful documentation, links, and articles:

[1]: https://app.datadoghq.com/account/settings/agent/latest
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: https://github.com/DataDog/integrations-core/blob/master/dcgm/datadog_checks/dcgm/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/dcgm/metadata.csv
[7]: https://github.com/DataDog/integrations-core/blob/master/dcgm/assets/service_checks.json
[8]: https://docs.datadoghq.com/help/
[9]: https://github.com/NVIDIA/dcgm-exporter/tree/main#changing-metrics
[10]: https://docs.nvidia.com/datacenter/dcgm/latest/dcgm-api/dcgm-api-field-ids.html
[11]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=kubernetes#configuration
[12]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=kubernetes
[13]: https://en.wikipedia.org/wiki/Operating_temperature
[14]: https://github.com/NVIDIA/dcgm-exporter/issues/163#issuecomment-1577506512
[15]: https://developer.nvidia.com/dcgm
[16]: https://github.com/NVIDIA/dcgm-exporter
[17]: https://docs.datadoghq.com/integrations/nvml/#metrics
