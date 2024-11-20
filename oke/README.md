# Oracle Container Engine for Kubernetes

## Overview

Oracle Cloud Infrastructure Container Engine for Kubernetes (OKE) is a managed Kubernetes service that simplifies the operations of enterprise-grade Kubernetes at scale. 

This integration collects metrics and tags from the [`oci_oke`][1] namespace to help you monitor your Kubernetes control plane, clusters, and node states. 

Deploying the [Datadog Agent][2] on your OKE cluster can also help you track the load on your clusters, pods, and individual nodes to get better insights into how to provision and deploy your resources.

In addition to monitoring your nodes, pods, and containers, the Agent can also collect and report metrics from the services running in your cluster, so that you can:

- Explore your OKE clusters with [pre-configured Kubernetes dashboards][3]
- Monitor containers and processes in real time
- Automatically track and monitor containerized services

## Setup

Once you set up the [Oracle Cloud Infrastructure][4] integration, ensure that the `oci_oke` namespace is included in your [Connector Hub][5].

Because Datadog already integrates with Kubernetes, it is ready-made to monitor OKE. If you're running the Agent in a Kubernetes cluster and plan to migrate to OKE, you can continue monitoring your cluster with Datadog.

Deploying the Agent as a DaemonSet with the [Helm chart][6] is the most straightforward (and recommended) method, since it ensures that the Agent will run as a pod on every node within your cluster and that each new node automatically has the Agent installed. You can also configure the Agent to collect process data, traces, and logs by adding a few extra lines to a Helm values file. Additionally, OKE node pools are supported.


## Troubleshooting

Need help? Contact [Datadog support][7].

## Further Reading

- [How to monitor OKE with Datadog][8]

[1]: https://docs.oracle.com/en-us/iaas/Content/ContEng/Reference/contengmetrics.htm
[2]: https://docs.datadoghq.com/agent/kubernetes/#installation
[3]: https://app.datadoghq.com/dashboard/lists/preset/3?q=kubernetes
[4]: https://docs.datadoghq.com/integrations/oracle_cloud_infrastructure/
[5]: https://cloud.oracle.com/connector-hub/service-connectors
[6]: https://docs.datadoghq.com/agent/kubernetes/?tab=helm
[7]: https://docs.datadoghq.com/help/
[8]: https://www.datadoghq.com/blog/monitor-oracle-kubernetes-engine/
