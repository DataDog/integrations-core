# Agent Check: Kuma

## Overview

This check monitors [Kuma][1], a universal open-source control plane for service mesh that supports both Kubernetes and Universal mode (VMs and standalone containers). [Kong Mesh][2], the enterprise edition of Kuma, is fully supported through this integration. Beyond the installation steps outlined here, no additional configuration is required.

With the Datadog Kuma integration, you can:
- Monitor the health and performance of the Kuma control plane.
- Collect logs from both the control plane and the data plane proxies.
- Gain detailed insights into the internal traffic flows within your service mesh which helps monitor performance and ensure reliability.

For monitoring the Envoy data planes (sidecars) within your Kuma mesh:
- Use the [Envoy integration][10] to collect metrics.
- Use this Kuma integration to collect logs.

**Minimum Agent version:** 7.68.0

## Setup

The Kuma check is included in the [Datadog Agent][3] package. No additional installation is needed on your server.

### Configuration

#### Metric collection

Metrics are collected from the Kuma control plane and the Envoy data planes.

##### Control plane

**Autodiscovery (Kubernetes)**

To configure the Agent to collect metrics from the Kuma control plane using autodiscovery, apply the following pod annotations to your `kuma-control-plane` deployment. This example assumes you installed Kuma using Helm. For more information about autodiscovery, see [Autodiscovery Integration Templates][4].

```yaml
# values.yaml
controlPlane:
  podAnnotations:
    ad.datadoghq.com/control-plane.checks: |
      {
        "kuma": {
          "init_config": {},
          "instances": [
            {
              "openmetrics_endpoint": "http://%%host%%:5680/metrics",
              "service": "kuma-control-plane"
            }
          ]
        }
      }
```

**Note:** The autodiscovery annotation for Kuma has the format `ad.datadoghq.com/<CONTAINER_NAME>.checks:`. 
If your control plane has a different name, change the line accordingly. For more information, see the [Datadog documentation][18].

**Configuration file**

Alternatively, you can configure the integration by editing the `kuma.d/conf.yaml` file in the `conf.d/` folder at the root of your Agent's configuration directory:

```yaml
instances:
  - openmetrics_endpoint: http://<KUMA_CONTROL_PLANE_HOST>:5680/metrics
    service: kuma-control-plane
```

See the [sample kuma.d/conf.yaml][5] for all available configuration options.

##### Data planes (Envoy proxies)

Metrics from the data planes are collected using the [Envoy integration][10].

1.  First, enable Prometheus metrics exposition on your data planes by creating a `MeshMetric` policy. For more details, see the [Kuma documentation][12].

    ```yaml
    apiVersion: kuma.io/v1alpha1
    kind: MeshMetric
    metadata:
      name: my-metrics-policy
      namespace: kuma-system
      labels:
        kuma.io/mesh: default
    spec:
      default:
        backends:
        - type: Prometheus
          prometheus:
            port: 5670
            path: "/metrics"
    ```

2.  Next, configure the Datadog Agent to collect these metrics by applying the following annotations to your application pods. For guidance on applying annotations, see [Autodiscovery Integration Templates][4].

    ```yaml
    ad.datadoghq.com/kuma-sidecar.checks: |
      {
        "envoy": {
          "instances": [
            {
              "openmetrics_endpoint": "http://%%host%%:5670/metrics",
              "collect_server_info": false
            }
          ]
        }
      }
    ```

    **Note:** The autodiscovery annotation for Kuma has the format `ad.datadoghq.com/<CONTAINER_NAME>.checks:`. 
    If your sidecar has a different name, change the line accordingly. For more information, see the [Datadog documentation][18].

#### Log collection

Enable log collection in your `datadog.yaml` file:

```yaml
logs_enabled: true
```

##### Control Plane Logs

To collect logs from the Kuma control plane, apply the following annotations to your `kuma-control-plane` deployment:

```yaml
# values.yaml
controlPlane:
  podAnnotations:
    ad.datadoghq.com/control-plane.logs: |
      [
        {
          "source": "kuma",
          "service": "kuma-control-plane"
        }
      ]
```

**Note:** The autodiscovery annotation for Kuma has the format `ad.datadoghq.com/<CONTAINER_NAME>.logs:`. 
If your control plane has a different name, change the line accordingly. For more information, see the [Datadog documentation][18].

##### Data plane logs

Configure the Datadog Agent to collect logs from the Envoy sidecar containers by applying the following annotations to your application pods:

```yaml
ad.datadoghq.com/kuma-sidecar.logs: |
  [
    {
      "source": "kuma",
      "service": "<MY_SERVICE>",
      "auto_multi_line_detection": true
    }
  ]
```

**Note:** The autodiscovery annotation for Kuma has the format `ad.datadoghq.com/<CONTAINER_NAME>.logs:`. 
If your sidecar has a different name, change the line accordingly. For more information, see the [Datadog documentation][18].

Replace `<MY_SERVICE>` with the name of your service.

**Optional: Enable mesh access logs**

If you want to collect access logs showing traffic between services in your mesh, you can enable them by creating a `MeshAccessLog` policy. For more details, see the [Kuma documentation][13].

### Enable sidecar injection for Datadog Agent pods

If you have strict [mTLS][14] enabled for your mesh, the Datadog Agent requires a Kuma sidecar to be injected into its pods to communicate with other services.

To enable sidecar injection for the Datadog Agent, add the `kuma.io/sidecar-injection: enabled` label to the namespace where the Agent is deployed (usually `datadog`):

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: datadog
  labels:
    kuma.io/sidecar-injection: enabled
```

You also need to apply a `MeshTrafficPermission` policy to allow traffic between the Agent and your services. For more information, see the [Kuma documentation][15].

### Validation

[Run the Agent's `status` subcommand][6] and look for `kuma` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this check.

### Events

The Kuma integration does not include any events.


## Troubleshooting

### mTLS connection issues

If you have strict mTLS with no passthrough enabled, the Agent may fail to connect to the control plane or other services. This is because all traffic is encrypted and routed through Kuma's data plane proxies. To resolve this, you must [enable sidecar injection for the Datadog Agent pods](#enable-sidecar-injection-for-datadog-agent-pods). 

Once the sidecar is injected, you should replace `%%host%%` with the Kubernetes service name in your autodiscovery annotations, as the `%%host%%` macro may no longer work correctly when traffic is routed through the mesh. This is not necessary for the Kuma control plane or sidecars.

For example, instead of:
```yaml
"openmetrics_endpoint": "http://%%host%%:5670/metrics"
```

Use the service name:
```yaml
"openmetrics_endpoint": "http://my-service.my-namespace.svc.cluster.local:5670/metrics"
```

When mTLS is enabled, you may want to disable auto-discovery auto-configuration since it uses `%%host%%` macros. For more information on how to disable auto-configuration, see the [Datadog documentation][17].

Need help? Contact [Datadog support][9].

## Further Reading

- [Kuma official documentation][1]
- [Kuma Policies Documentation][16]

[1]: https://kuma.io/
[2]: https://konghq.com/products/kong-mesh
[3]: /account/settings/agent/latest
[4]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[5]: https://github.com/DataDog/integrations-core/blob/master/kuma/datadog_checks/kuma/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/kuma/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/kuma/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.datadoghq.com/integrations/envoy/
[11]: https://docs.datadoghq.com/integrations/openmetrics/
[12]: https://kuma.io/docs/latest/policies/meshmetric/
[13]: https://kuma.io/docs/latest/policies/meshaccesslog/
[14]: https://kuma.io/docs/2.11.x/quickstart/kubernetes-demo/#introduce-zero-trust-security
[15]: https://kuma.io/docs/latest/policies/meshtrafficpermission/
[16]: https://kuma.io/docs/latest/policies/meshtrafficpermission/
[17]: https://docs.datadoghq.com/containers/guide/auto_conf/?tab=datadogoperator#disable-auto-configuration
[18]: https://docs.datadoghq.com/containers/kubernetes/integrations/?tab=annotations
