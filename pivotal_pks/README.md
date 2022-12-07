# Pivotal Container Service Integration

## Overview

This integration monitors [Pivotal Container Service][1] clusters.

## Setup

Since Datadog already integrates with Kubernetes, it is ready-made to monitor Pivotal Kubernetes Service (PKS). You can use the Datadog [Cluster Monitoring tile][7] along with this integration to monitor your cluster.

Install the Datadog Agent on each non-worker VM in your PKS environment. In environments without Pivotal Application Service (PAS) installed, select the `Resource Config` section of the tile and set `instances` of the `datadog-firehose-nozzle` to `0`.

### Metric collection

Monitoring PKS requires that you set up the Datadog integration for [Kubernetes][2].

### Log collection

_Available for Agent versions >6.0_

The setup is exactly the same as for Kubernetes.
To start collecting logs from all your containers, use your Datadog Agent [environment variables][3].

You can also take advantage of DaemonSets to [automatically deploy the Datadog Agent on all your nodes][4].

Follow the [container log collection steps][5] to learn more about those environment variables and discover more advanced setup options.

## Troubleshooting

Need help? Contact [Datadog support][6].

[1]: https://pivotal.io/platform/pivotal-container-service
[2]: https://docs.datadoghq.com/integrations/kubernetes/
[3]: https://docs.datadoghq.com/agent/basic_agent_usage/kubernetes/#log-collection-setup
[4]: https://docs.datadoghq.com/agent/basic_agent_usage/kubernetes/#container-installation
[5]: https://docs.datadoghq.com/logs/log_collection/docker/#option-2-container-installation
[6]: https://docs.datadoghq.com/help/
[7]: https://network.pivotal.io/products/datadog
