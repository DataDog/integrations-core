# Agent Check: DCGM

## Overview

This check submits metrics exposed by the [Nvidia DCGM][15] [Exporter][16] in Datadog Agent format.

## Setup

### Installation

The DCGM check is included in the [Datadog Agent][1] package. However, you need to spin up the DCGM Exporter container to expose the GPU metrics in order for the Agent to collect this data.

<!-- xxx tabs xxx -->
<!-- xxx tab "Host | Docker" xxx -->

#### Docker

To configure the exporter in a Docker environment:

1. Create the following file `$PWD/default-counters.csv` which contains the default fields from `etc/default-counters.csv`. To add more fields for collection, follow [these instructions][9]. For the complete list of fields, see the [DCGM API reference manual][10].

<div class="alert alert-info">Datadog recommends adding the following fields to cover the same ground as the <a href="https://docs.datadoghq.com/integrations/nvml/#metrics">NVML integration</a>:

```
DCGM_FI_DEV_COUNT,                       counter, Number of Devices on the node.
DCGM_FI_DEV_FAN_SPEED,                   gauge,   Fan speed for the device in percent 0-100.
DCGM_FI_PROCESS_NAME,                    label,   The Process Name.
DCGM_FI_PROF_PCIE_TX_BYTES,              counter, Total number of bytes transmitted through PCIe TX (in KB) via NVML.
DCGM_FI_PROF_PCIE_RX_BYTES,              counter, Total number of bytes received through PCIe RX (in KB) via NVML.
```

It is also recommended enabling the following default counters and labels:
- `DCGM_FI_DEV_MEMORY_TEMP`
- `DCGM_FI_DEV_GPU_TEMP`
- `DCGM_FI_DEV_POWER_USAGE`
- `DCGM_FI_DEV_TOTAL_ENERGY_CONSUMPTION`
- `DCGM_FI_DEV_GPU_UTIL`
- `DCGM_FI_DEV_MEM_COPY_UTIL`
- `DCGM_FI_DEV_FB_FREE`
- `DCGM_FI_DEV_FB_USED`
- `DCGM_FI_DRIVER_VERSION`
- `DCGM_FI_DEV_NAME`
- `DCGM_FI_DEV_BRAND`
- `DCGM_FI_DEV_SERIAL`

The following non-default fields and labels are also recommended:
```
DCGM_FI_DEV_SLOWDOWN_TEMP,              gauge, Slowdown temperature for the device.
DCGM_FI_DEV_POWER_MGMT_LIMIT,           gauge, Current power limit for the device.
DCGM_FI_DEV_PSTATE,                     gauge, Performance state (P-State) 0-15. 0=highest
DCGM_FI_DEV_FB_TOTAL,                   gauge,
DCGM_FI_DEV_FB_RESERVED,                gauge,
DCGM_FI_DEV_FB_USED_PERCENT,            gauge,
DCGM_FI_DEV_CLOCK_THROTTLE_REASONS,     gauge, Current clock throttle reasons (bitmask of DCGM_CLOCKS_THROTTLE_REASON_*)
DCGM_FI_CUDA_DRIVER_VERSION,            label,
DCGM_FI_DEV_NAME,                       label,
DCGM_FI_DEV_MINOR_NUMBER,               label,
```
</div>

2. Run the Docker container using the following command:
```
sudo docker run --pid=host --privileged -e DCGM_EXPORTER_INTERVAL=3 --gpus all -d -v /proc:/proc -v $PWD/default-counters.csv:/etc/dcgm-exporter/default-counters.csv -p 9400:9400 --name dcgm-exporter nvcr.io/nvidia/k8s/dcgm-exporter:3.1.7-3.1.4-ubuntu20.04
```

<!-- xxz tab xxx -->
<!-- xxx tab "Kubernetes" xxx -->

#### Kubernetes

1. To configure the Exporter in a Kubernetes environment, please review the template provided by NVIDIA here:

- https://github.com/iliakur/dcgm-exporter#quickstart-on-kubernetes


<!-- xxz tab xxx -->
<!-- xxx tab "Operator" xxx -->

#### Operator

To configure the Exporter in an Operator environment, please review the template provided by NVIDIA here:

- https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/getting-started.html#gpu-telemetry

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

Use the `extra_metrics` configuration field to add metrics that go beyond the ones [we support out of the box][6]. See [here][10] for the full list of metrics that dcgm-exporter can collect. Make sure to [enable these fields in the dcgm-exporter configuration][9] as well.

<!-- xxx tab xxx -->
<!-- xxx tab "Docker" xxx -->

#### Docker

1. To configure this check for an Agent running on a container:

##### Metric collection

Set [Autodiscovery Integrations Templates][5] as Docker labels on your application container:

```yaml
LABEL "com.datadoghq.ad.check_names"='["dcgm"]'
LABEL "com.datadoghq.ad.init_configs"='[{}]'
LABEL "com.datadoghq.ad.instances"='[{"openmetrics_endpoint": "http://%%host%%:9400/metrics"}]'
```

<!-- xxz tab xxx -->
<!-- xxx tab "Kubernetes" xxx -->

#### Kubernetes

1. To configure this check for an Agent running on Kubernetes:

##### Metric collection

Set [Autodiscovery Integrations Templates][12] as pod annotations on your application container. Aside from this, templates can also be configured with [a file, a configmap, or a key-value store][11].

**Annotations v1** (for Datadog Agent < v7.36)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: '<POD_NAME>'
  annotations:
    ad.datadoghq.com/dcgm.check_names: '["dcgm"]'
    ad.datadoghq.com/dcgm.init_configs: '[{}]'
    ad.datadoghq.com/dcgm.instances: |
      [
        {
          "openmetrics_endpoint": "http://%%host%%:9400/metrics"
        }
      ]
spec:
  containers:
    - name: dcgm
```

**Annotations v2** (for Datadog Agent v7.36+)

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


<!-- xxz tabs xxx -->

2. [Restart the Agent][4].

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

If you have added some metrics that don't appear in the [metadata.csv][6] above but appear in your account with the format `DCGM_FI_DEV_NEW_METRIC`, it is important to remap these metrics in the [dcgm.d/conf.yaml][3] configuration file:
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

It may happen that you've enabled the collection of a field in `default-counters.csv`, but it doesn't appear up in Datadog, even after making a `curl` request to `host:9400/metrics`.
To figure out why this field is not being collected, [dcgm-exporter devs recommend][14] looking at the file `var/log/nv-hostengine.log`.
Keep in mind that `dcgm-exporter` is a thin wrapper around lower-level libraries and drivers which do the actual reporting.

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
