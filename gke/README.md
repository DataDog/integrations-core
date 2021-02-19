# GKE Integration

## Overview

Google Kubernetes Engine (GKE), a service on the Google Cloud Platform (GCP), is a hosted platform for running and orchestrating containerized applications. Similar to Amazon’s Elastic Container Service (ECS), GKE manages Docker containers deployed on a cluster of machines. However, unlike ECS, GKE uses Kubernetes.

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

### Metric collection

Deploy a [containerized version of the Datadog Agent][7] on your Kubernetes cluster. 

You can deploy the Agent with a Helm chart or directly with a [DaemonSet][8].

[1]: https://cloud.google.com/resource-manager/docs/creating-managing-projects
[2]: https://console.cloud.google.com/apis/api/container.googleapis.com
[3]: https://cloud.google.com/sdk/docs/
[4]: https://cloud.google.com/sdk/docs/initializing
[5]: /integrations/google_cloud_platform/
[6]: https://app.datadoghq.com/screen/integration/gce
[7]: https://app.datadoghq.com/account/settings#agent/kubernetes
[8]: https://docs.datadoghq.com/agent/kubernetes/?tab=daemonset