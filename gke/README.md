# GKE Integration

## Overview

Google Kubernetes Engine (GKE), a service on the Google Cloud Platform (GCP), is a hosted platform for running and orchestrating containerized applications. Similar to Amazon's Elastic Container Service (ECS), GKE manages Docker containers deployed on a cluster of machines. However, unlike ECS, GKE uses Kubernetes.

## Setup

### Prerequisites

1. Ensure that your role in your [GCP project][1] has the proper permissions to use GKE. 

2. Enable the [Google Container Engine API][2] for your project. 

3. Install the [Google Cloud SDK][3] and the `kubectl` command line tool on your local machine. Once you [pair the Cloud SDK with your GCP account][4], you can control your clusters directly from your local machine using `kubectl`.

4. Create a small GKE cluster named `doglib` with the ability to access the Cloud Datastore by running the following command:

```
$  gcloud container clusters create doglib --num-nodes 3 --zone "us-central1-b" --scopes "cloud-platform"
```

### Set up the GCE integration 

Install the [Google Cloud Platform][5] integration.

You can then access an out-of-the-box [Google Compute Engine dashboard][6] that displays metrics like disk I/O, CPU utilization, and network traffic.

### Set up the GKE integration

Choose a mode of operation. A *mode of operation* refers to the level of flexibility, responsibility, and control that you have over your cluster. GKE offers two modes of operation:

- **Standard**: You manage the cluster's underlying infrastructure, giving you node configuration flexibility.

- **Autopilot**: Google provisions and manages the entire cluster's underlying infrastructure, including nodes and node pools, giving you an optimized cluster with a hands-off experience.

<!-- xxx tabs xxx -->
<!-- xxx tab "Standard" xxx -->

#### Standard

Deploy a [containerized version of the Datadog Agent][7] on your Kubernetes cluster. 

You can deploy the Agent with a [Helm chart][8] or directly with a [DaemonSet][9].


<!-- xxz tab xxx -->
<!-- xxx tab "Autopilot" xxx -->

#### Autopilot

1. Install Helm.

2. Add the Datadog repository to your Helm repositories:

  ```bash
  helm repo add datadog https://helm.datadoghq.com
  helm repo update
  ```

3. Deploy the Datadog Agent and Cluster Agent on Autopilot with the following command:

  ```bash
  helm install <RELEASE_NAME> \
      --set datadog.apiKey=<DATADOG_API_KEY> \
      --set datadog.appKey=<DATADOG_APP_KEY> \
      --set clusterAgent.enabled=true \
      --set clusterAgent.metricsProvider.enabled=true \
      --set providers.gke.autopilot=true \
      datadog/datadog
  ```

  **Note**: If you also wish to enable logs or traces, add lines to this command setting `datadog.logs.enabled` (for logs) and `datadog.apm.enabled` (for traces) to `true`. For example:

  ```bash
  helm install --name <RELEASE_NAME> \
      --set datadog.apiKey=<DATADOG_API_KEY> \
      --set datadog.appKey=<DATADOG_APP_KEY> \
      --set clusterAgent.enabled=true \
      --set clusterAgent.metricsProvider.enabled=true \
      --set providers.gke.autopilot=true \
      --set datadog.logs.enabled=true \
      --set datadog.apm.enabled=true \
      datadog/datadog
  ```

  See the [Datadog helm-charts repository][10] for a full list of configurable values.

 **A note on the Admission Controller**
 
 If you wish to use the [admission controller]([url](https://docs.datadoghq.com/containers/cluster_agent/admission_controller/?tab=operator)) with Autopilot, you must set the `configMode` of the admission controller to either `service` or `hostip` ([setting here]([url](https://github.com/DataDog/helm-charts/blob/main/charts/datadog/values.yaml#L922))). This is because the `socket` mode is not allowed due to autopilot restrictions. Instead, we recommend using `service` (with `hostip` as a fallback), to provide a more robust layer of abstraction for the controller. 
<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

## Further Reading

- [Announcing support for GKE Autopilot][11]

[1]: https://cloud.google.com/resource-manager/docs/creating-managing-projects
[2]: https://console.cloud.google.com/apis/api/container.googleapis.com
[3]: https://cloud.google.com/sdk/docs/
[4]: https://cloud.google.com/sdk/docs/initializing
[5]: /integrations/google_cloud_platform/
[6]: https://app.datadoghq.com/screen/integration/gce
[7]: https://app.datadoghq.com/account/settings#agent/kubernetes
[8]: https://docs.datadoghq.com/agent/kubernetes/?tab=helm
[9]: https://docs.datadoghq.com/agent/kubernetes/?tab=daemonset
[10]: https://github.com/DataDog/helm-charts/tree/master/charts/datadog#values
[11]: https://www.datadoghq.com/blog/gke-autopilot-monitoring/
