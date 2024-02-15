# Agent Check: Calico

## Overview

This check monitors [Calico][1] through the Datadog Agent.

The Calico check sends metrics concerning network and security in a Kubernetes cluster set up with Calico.

## Setup

### Installation

The Calico check is included in the [Datadog Agent][2] package. 

#### Installation with a Kubernetes cluster-based Agent

Using annotations:

1. Set up Calico on your cluster.

2. Enable Prometheus metrics using the instructions in [Monitor Calico component metrics][9].
   Once enabled, you should have a `felix-metrics-svc` service running in your cluster, as well as a `prometheus-pod`.

3. To use Autodiscovery, modify `prometheus-pod`. Add the following snippet to your Prometheus YAML configuration file:

   ```
   metadata:
     [...]
     annotations:
      ad.datadoghq.com/prometheus-pod.check_names: |
      ["openmetrics"]
      ad.datadoghq.com/prometheus-pod.init_configs: |
      [{}]
      ad.datadoghq.com/prometheus-pod.instances: |
        [
           {
              "prometheus_url": "http://<FELIX-SERVICE-IP>:<FELIX-SERVICE-PORT>/metrics",
              "namespace": "calico",
              "metrics": ["*"]
           }
        ]
     spec:
       [....]
   ```

You can find values for `<FELIX-SERVICE-IP>` and `<FELIX-SERVICE-PORT>` by running `kubectl get all -all-namespaces`.

#### Installation with an OS-based Agent

1. Follow [Monitor Calico component metrics][9] until you have a `felix-metrics-svc` service running by using `kubectl get all --all-namespaces`.

2. If you are using minikube, you must forward port 9091 to `felix-metrics-svc`.
   Run `kubectl port-forward service/felix-metrics-svc 9091:9091 -n kube-system`.

   If you are not using minikube, check that `felix-metrics-svc` has an external IP. If the service does not have an external IP, use `kubectl edit svc` to change its type from `ClusterIP` to `LoadBalancer`.


### Configuration

Follow the instructions to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

1. Edit the `calico.d/conf.yaml` file in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Calico performance data.
   The only required parameter is the `openmetrics_endpoint` URL. See the [sample calico.d/conf.yaml][3] for all available configuration options.

2. If you are using minikube, use 'http://localhost:9091/metrics' as your `openmetrics_endpoint` URL.
   If you are not using minikube, use `http://<FELIX-METRICS-SVC-EXTERNAL-IP>:<PORT>/metrics` as your `openmetrics_endpoint` URL.

3. [Restart the Agent][4].

##### Metric collection

1. The default configuration of your `calico.d/conf.yaml` file activate the collection of your [Calico metrics](#metrics). See the [sample calico.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4].

##### Log collection

Since Calico structure is set up in a Kubernetes cluster, it is built with deployments, pods, and services. The Kubernetes integration fetches logs from containers.

After setting up the [Kubernetes][12] integration, Calico logs become available in the Datadog Log Explorer.

Collecting logs is disabled by default in the Datadog Agent. Enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```
   
<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][13] for guidance on applying the parameters below. 

##### Metric collection

| Parameter            | Value                                                      |
|----------------------|------------------------------------------------------------|
| `<INTEGRATION_NAME>` | `calico`                                                   |
| `<INIT_CONFIG>`      | blank or `{}`                                              |
| `<INSTANCE_CONFIG>`  | `{openmetrics_endpoint: <OPENMETRICS_ENDPOINT>}`           |

##### Log collection

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][14].

| Parameter      | Value                                                  |
| -------------- | ------------------------------------------------------ |
| `<LOG_CONFIG>` | `{"source": "calico", "service": "<SERVICE_NAME>"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][5] and look for `calico` under the Checks section.

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Events

The Calico integration does not include any events.

### Service Checks

See [service_checks.json][7] for a list of service checks provided by this integration.


## Troubleshooting

Need help? Contact [Datadog support][8].

## Further Reading

Additional helpful documentation, links, and articles:

- [Monitor Calico with Datadog][15]

[1]: https://www.tigera.io/project-calico/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://github.com/DataDog/integrations-core/blob/master/calico/datadog_checks/calico/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/calico/metadata.csv
[7]: https://github.com/DataDog/integrations-core/blob/master/calico/assets/service_checks.json
[8]: https://docs.datadoghq.com/help/
[9]: https://docs.tigera.io/calico/3.25/operations/monitor/monitor-component-metrics
[10]: https://docs.datadoghq.com/developers/integrations/python/
[11]: https://app.datadoghq.com/account/settings/agent/latest
[12]: https://docs.datadoghq.com/agent/kubernetes
[13]: https://docs.datadoghq.com/agent/docker/integrations/?tab=docker
[14]: https://docs.datadoghq.com/agent/kubernetes/log/?tab=containerinstallation#setup
[15]: https://www.datadoghq.com/blog/monitor-calico-with-datadog/
