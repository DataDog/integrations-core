
# Agent Check: Kong Mesh

## Overview

This check monitors [Kong Mesh][1], a universal open-source control plane for service mesh that supports both Kubernetes and Universal mode (VMs and standalone containers). Kong Mesh is the enterprise version of [Kuma][2], developed by Kong.

With the Datadog Kong Mesh integration, you can:
- Monitor the health and performance of the Kong Mesh control plane.
- Collect logs from both the control plane and the data plane proxies.
- Gain detailed insights into the internal traffic flows within your service mesh which helps monitor performance and ensure reliability.

For monitoring Kong Mesh (control plane and Envoy data planes):
- Use the [Kuma integration][3] to collect both metrics and logs. Follow the [Configuration instructions][5] in the Kuma documentation.
- This integration provides prebuilt dashboards and monitors for convenience. Kong Mesh can be fully monitored using only the Kuma integration, which also includes dashboards and monitors.

**Note:** You can also use the [Kuma integration][3] to monitor your Kong Mesh deployment.

## Setup

The `Kuma` Agent check — which the Kong Mesh integration relies on — is included in the [Datadog Agent][4] package. No additional installation is needed on your server.

### Configuration

#### Metric collection

Metrics are collected from the control plane and the Envoy data planes. Refer to the [Kuma integration documentation][5] to set up metrics collection.

#### Log collection

Logs are collected from control plane and the Envoy data planes. Refer to the [Kuma integration documentation][5] to set up logs collection.

**Note:** For the `source` property in the logs configuration, you can optionally replace or `kuma` with `kong_mesh`. 


### Events

The Kong Mesh integration does not include any events.

## Troubleshooting

Refer to the troubleshooting section of the [Kuma integration documentation][6] for troubleshooting steps.

Need help? Contact [Datadog support][7].

[1]: https://konghq.com/products/kong-mesh
[2]: https://kuma.io/
[3]: https://docs.datadoghq.com/integrations/kuma/#overview
[4]: /account/settings/agent/latest
[5]: https://docs.datadoghq.com/integrations/kuma/#configuration
[6]: https://docs.datadoghq.com/integrations/kuma/#troubleshooting
[7]: https://docs.datadoghq.com/help/