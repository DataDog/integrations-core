# Agent Check: DCGM

## Overview

Harnessing the Nvidia DCGM Exporter, this check monitors the exposed [GPU metrics][1] through the Datadog Agent.

## Setup

### Installation

The DCGM check is included in the [Datadog Agent][2] package, however we will need to spin up the DCGM Exporter container to expose the GPU metrics for the Agent to collect.

<!-- xxx tabs xxx -->
<!-- xxx tab "Host | Docker" xxx -->

#### Docker

To configure the exporter in a Docker environment:

1. Create the following file `$PWD/default-counters.csv` which contains the default metrics from the `etc/default-counters.csv`. Using this file, we can add more metrics for collection and can be done by adding the counter name, type and description to the end of the file. For reference on adding metrics, please see the [Changing Metrics][10] section and for the complete list of counters, see the [DCGM API reference manual][11]. 
<div class="alert alert-info">We recommend adding the following to cover those that are found in the <a href="https://docs.datadoghq.com/integrations/nvml/#metrics">NVML integration</a>:

```
DCGM_FI_DEV_COUNT,                       counter, Number of Devices on the node.
DCGM_FI_DEV_FAN_SPEED,                   gauge,   Fan speed for the device in percent 0-100.
DCGM_FI_PROCESS_NAME,                    label,   The Process Name.
DCGM_FI_PROF_PCIE_TX_BYTES,              counter, Total number of bytes transmitted through PCIe TX (in KB) via NVML.
DCGM_FI_PROF_PCIE_RX_BYTES,              counter, Total number of bytes received through PCIe RX (in KB) via NVML.
```
</div>

3. Run the Docker container using the following command:
```
sudo docker run --pid=host --privileged -e DCGM_EXPORTER_INTERVAL=3 --gpus all -d -v /proc:/proc -v $PWD/default-counters.csv:/etc/dcgm-exporter/default-counters.csv -p 9400:9400 --name dcgm-exporter nvcr.io/nvidia/k8s/dcgm-exporter:3.1.7-3.1.4-ubuntu20.04
```

<!-- xxz tab xxx -->
<!-- xxx tab "Kubernetes" xxx -->

#### Kubernetes

1. To configure the Exporter in a Kubernetes environment, please review the template provided by NVIDIA here:

- https://github.com/NVIDIA/dcgm-exporter/blob/main/dcgm-exporter.yaml 


<!-- xxz tab xxx -->
<!-- xxx tab "Operator" xxx -->

#### Operator

1. To configure the Exporter in an Operator environment, please review the template provided by NVIDIA here:

- https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/getting-started.html#gpu-telemetry

<!-- xxz tabs xxx -->


### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

##### Metric collection

1. Edit the `dcgm.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your GPU Metrics. See the [sample dcgm.d/conf.yaml][4] for all available configuration options.

```
instances:

    ## @param openmetrics_endpoint - string - required
    ## The URL exposing metrics in the OpenMetrics format.
    ##
    ## Set this to <listenAddress>/<handlerPath> as configured in your DCGM Server
    #
    - openmetrics_endpoint: http://localhost:9400/metrics
```

<!-- xxx tab xxx -->
<!-- xxx tab "Docker" xxx -->

#### Docker

1. To configure this check for an Agent running on a container:

##### Metric collection

Set [Autodiscovery Integrations Templates][7] as Docker labels on your application container:

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

Set [Autodiscovery Integrations Templates][13] as pod annotations on your application container. Aside from this, templates can also be configured with [a file, a configmap, or a key-value store][12].

**Annotations v1** (for Datadog Agent < v7.36)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: dcgm-exporter #TODO should this be be podname or check name?
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
  name: dcgm-exporter #TODO should this be be podname or check name?
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

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `dcgm` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The DCGM integration does not include any events.

### Service Checks

The dcgm integration does not include any service checks.

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

### Metric Mapping

If you have added some metrics that don't appear in the [metadata.csv][7] above and appear in your account with the format `DCGM_FI_DEV_NEW_METRIC`, it is important to remap these metrics in the [dcgm.d/conf.yaml][4] configuration file:
```yaml
    ## @param extra_metrics - (list of string or mapping) - optional
    ## This list defines metrics to collect from the `openmetrics_endpoint`, in addition to
    ## what the check collects by default. If the check already collects a metric, then
    ## metric definitions here take precedence. Metrics may be defined in 3 ways:
    ...
```
The example below will append the part in `NEW_METRIC` to the namespace (`dcgm.`), giving `dcgm.new_metric`:

```yaml
    extra_metrics:
    - DCGM_FI_DEV_NEW_METRIC: new_metric
```

## Further Reading

Additional helpful documentation, links, and articles:

<!-- Blog Posts on the way ? -->


Need help? Contact [Datadog support][9].



<!-- TODO NEED TO SORT OUT ALL INTEGRATION REFERENCES -->
[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/dcgm/datadog_checks/dcgm/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/dcgm/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/dcgm/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://github.com/NVIDIA/dcgm-exporter/tree/main#changing-metrics
[11]: https://docs.nvidia.com/datacenter/dcgm/latest/dcgm-api/dcgm-api-field-ids.html 
[12]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=kubernetes#configuration
[13]: https://docs.datadoghq.com/agent/kubernetes/integrations/?tab=kubernetes
