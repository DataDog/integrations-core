# GKE Integration

## Overview

Google Kubernetes Engine (GKE), a service on the Google Cloud Platform (GCP), is a hosted platform for running and orchestrating containerized applications backed by Kubernetes. GKE clusters can be monitored by the [Google Cloud Platform][5] integration as well as by the Datadog Agent running as workloads within the cluster.

## Setup

### Prerequisites

1. Ensure that your role in your [GCP project][1] has the proper permissions to use GKE. 

2. Enable the [Google Container Engine API][2] for your project. 

3. Install the [Google Cloud SDK][3] and the `kubectl` command line tool on your local machine. Once you [pair the Cloud SDK with your GCP account][4], you can control your clusters directly from your local machine using `kubectl`.

### Set up the GCE integration 

Install the [Google Cloud Platform][5] integration.

You can then access an out-of-the-box [Google Compute Engine dashboard][6] that displays metrics like disk I/O, CPU utilization, and network traffic.

### Set up the Kubernetes integration

To further monitor your GKE cluster, install the Datadog Agent using the Datadog Helm Chart or Datadog Operator. Once deployed, the Datadog Agent and Datadog Cluster Agent monitor your cluster and the workloads on it.

GKE supports two [main modes of operation][15] that can change the level of flexibility, responsibility, and control that you have over your cluster. These different modes change how you deploy the Datadog components.

- **Standard**: You manage the cluster's underlying infrastructure, giving you node configuration flexibility.

- **Autopilot**: Google provisions and manages the entire cluster's underlying infrastructure, including nodes and node pools, giving you an optimized cluster with a hands-off experience.

<!-- xxx tabs xxx -->
<!-- xxx tab "Standard" xxx -->

#### Standard

Deploy a [containerized version of the Datadog Agent][7] on your Kubernetes cluster. See [Install the Datadog Agent on Kubernetes][8].


<!-- xxz tab xxx -->
<!-- xxx tab "Autopilot" xxx -->

#### Autopilot

Autopilot requires a more distinct setup for the Kubernetes installation compared to the standard installation. This type of cluster requires using the Datadog Helm chart.

Deploy a [containerized version of the Datadog Agent][7] on your Kubernetes cluster with the Helm [installation of the Datadog Agent on Kubernetes][16]. When setting your Helm `datadog-values.yaml` configuration, see the [GKE Autopilot section on the Kubernetes Distributions][14] for the necessary configuration changes. Most notably, set `providers.gke.autopilot` to `true`.

#### Admission Controller
 
To use [Admission Controller][102] with Autopilot, set the [`configMode`][103] of the Admission Controller to either `service` or `hostip`. 

Because Autopilot does not allow `socket` mode, Datadog recommends using `service` (with `hostip` as a fallback) to provide a more robust layer of abstraction for the controller. 

[101]: https://github.com/DataDog/helm-charts/tree/master/charts/datadog#values
[102]: https://docs.datadoghq.com/containers/cluster_agent/admission_controller/?tab=operator
[103]: https://github.com/DataDog/helm-charts/blob/datadog-3.110.0/charts/datadog/values.yaml#L1284-L1293


<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

## Further Reading

- [Monitor GKE Autopilot with Datadog][10]
- [Monitor GKE with Datadog][11]
- [Monitor your T2A-powered GKE workloads with Datadog][12]
- [New GKE dashboards and metrics provide deeper visibility into your environment][13]

[1]: https://cloud.google.com/resource-manager/docs/creating-managing-projects
[2]: https://console.cloud.google.com/apis/api/container.googleapis.com
[3]: https://cloud.google.com/sdk/docs/
[4]: https://cloud.google.com/sdk/docs/initializing
[5]: /integrations/google_cloud_platform/
[6]: /screen/integration/gce
[7]: /account/settings/agent/latest?platform=kubernetes
[8]: https://docs.datadoghq.com/containers/kubernetes/installation?tab=operator
[9]: https://github.com/DataDog/helm-charts/tree/master/charts/datadog#values
[10]: https://www.datadoghq.com/blog/gke-autopilot-monitoring/
[11]: https://www.datadoghq.com/blog/monitor-google-kubernetes-engine/
[12]: https://www.datadoghq.com/blog/monitor-tau-t2a-gke-workloads-with-datadog-arm-support/
[13]: https://www.datadoghq.com/blog/gke-dashboards-integration-improvements/
[14]: https://docs.datadoghq.com/containers/kubernetes/distributions/?tab=helm#autopilot
[15]: https://cloud.google.com/kubernetes-engine/docs/concepts/choose-cluster-mode
[16]: https://docs.datadoghq.com/containers/kubernetes/installation?tab=helm
