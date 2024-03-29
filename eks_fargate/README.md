# Agent Check: eks_fargate

## Overview

<div class="alert alert-warning"> This page describes the EKS Fargate integration. For ECS Fargate, see the documentation for Datadog's <a href="http://docs.datadoghq.com/integrations/ecs_fargate">ECS Fargate integration</a>.
</div>

Amazon EKS on AWS Fargate is a managed Kubernetes service that automates certain aspects of deployment and maintenance for any standard Kubernetes environment. Kubernetes nodes are managed by AWS Fargate and abstracted away from the user.

**Note**: Network Performance Monitoring (NPM) is not supported for EKS Fargate.

## Setup

These steps cover the setup of the Datadog Agent v7.17+ in a container within Amazon EKS on AWS Fargate. See the [Datadog-Amazon EKS integration documentation][2] if you are not using AWS Fargate.

AWS Fargate pods are not physical pods, which means they exclude [host-based system-checks][3], like CPU, memory, etc. In order to collect data from your AWS Fargate pods, you must run the Agent as a sidecar of your application pod with custom RBAC, which enables these features:

- Kubernetes metrics collection from the pod running your application containers and the Agent
- [Autodiscovery][4]
- Configuration of custom Agent Checks to target containers in the same pod
- APM and DogStatsD for containers in the same pod

### EC2 Node

If you don't specify through [AWS Fargate Profile][5] that your pods should run on fargate, your pods can use classical EC2 machines. If it's the case see the [Datadog-Amazon EKS integration setup][6] in order to collect data from them. This works by running the Agent as an EC2-type workload. The Agent setup is the same as that of the [Kubernetes Agent setup][7], and all options are available. To deploy the Agent on EC2 nodes, use the [DaemonSet setup for the Datadog Agent][8].

### Installation

To get the best observability coverage monitoring workloads in AWS EKS Fargate, install the Datadog integrations for:

- [Kubernetes][9]
- [AWS][10]
- [EKS][11]
- [EC2][12] (if you are running an EC2-type node)

Also, set up integrations for any other AWS services you are running with EKS (for example, [ELB][13]).

#### Manual installation

To install, download the custom Agent image: `datadog/agent` with version v7.17 or above.

If the Agent is running as a sidecar, it can communicate only with containers on the same pod. Run an Agent for every pod you wish to monitor.

### Configuration

To collect data from your applications running in AWS EKS Fargate over a Fargate node, follow these setup steps:

- [Set up AWS EKS Fargate RBAC rules](#aws-eks-fargate-rbac).
- [Deploy the Agent as a sidecar](#running-the-agent-as-a-sidecar).
- Set up Datadog [metrics](#metrics-collection), [logs](#log-collection), [events](#events-collection), and [traces](#traces-collection) collection.

To have EKS Fargate containers in the Datadog Live Container View, enable `shareProcessNamespace` on your pod spec. See [Process Collection](#process-collection).

#### AWS EKS Fargate RBAC

Use the following Agent RBAC when deploying the Agent as a sidecar in AWS EKS Fargate:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: datadog-agent
rules:
  - apiGroups:
    - ""
    resources:
    - nodes
    - namespaces
    - endpoints
    verbs:
    - get
    - list
  - apiGroups:
      - ""
    resources:
      - nodes/metrics
      - nodes/spec
      - nodes/stats
      - nodes/proxy
      - nodes/pods
      - nodes/healthz
    verbs:
      - get
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: datadog-agent
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: datadog-agent
subjects:
  - kind: ServiceAccount
    name: datadog-agent
    namespace: default
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: datadog-agent
  namespace: default
```

#### Running the Agent as a sidecar

You can run the Agent as a sidecar by using the [Datadog Admission Controller][36] (requires Cluster Agent v7.52+) or with manual sidecar configuration. With the Admission Controller, you can inject an Agent sidecar into every pod that has the label `agent.datadoghq.com/sidecar:fargate`. 

With manual configuration, you must modify every workload manifest when adding or changing the Agent sidecar. Datadog recommends you use the Admission Controller.

<!-- xxx tabs xxx -->
<!-- xxx tab "Admission Controller" xxx -->
##### Admission Controller

<div class="alert alert-warning">This feature requires Cluster Agent v7.52.0+ and the <a href="http://docs.datadoghq.com/integrations/ecs_fargate">ECS Fargate integration</a>.
</div>

The setup below configures the Cluster Agent to communicate with the Agent sidecars, allowing access to features such as [events collection][29], [Kubernetes resources view][30], and [cluster checks][31].

**Prerequisites**

* Set up RBAC in the application namespace(s). See the [AWS EKS Fargate RBAC](#aws-eks-fargate-rbac) section on this page.
* Create a Kubernetes secret containing your Datadog API key and Cluster Agent token in the Datadog installation and application namespaces:

   ```shell
   kubectl create secret generic datadog-secret -n datadog-agent \
           --from-literal api-key=<YOUR_DATADOG_API_KEY> --from-literal token=<CLUSTER_AGENT_ TOKEN>
   kubectl create secret generic datadog-secret -n fargate \
           --from-literal api-key=<YOUR_DATADOG_API_KEY> --from-literal token=<CLUSTER_AGENT_TOKEN>
   ```
   For more information how these secrets are used, see the [Cluster Agent Setup][35].

###### Setup

1. Install the Datadog Agent with the Cluster Agent and Admission Controller enabled:

   ```sh
   helm install datadog datadog/datadog -n datadog-agent \
       --set datadog.clusterName=cluster-name \
       --set agents.enabled=false \
       --set datadog.apiKeyExistingSecret=datadog-secret \
       --set clusterAgent.tokenExistingSecret=datadog-secret \
       --set clusterAgent.admissionController.agentSidecarInjection.enabled=true \
       --set clusterAgent.admissionController.agentSidecarInjection.provider=fargate
   ```
   **Note**: Use `agents.enabled=false` for a Fargate-only cluster. On a mixed cluster, set `agents.enabled=true` to create a DaemonSet for monitoring workloads on EC2 instances.

2. After the Cluster Agent reaches a running state and registers Admission Controller mutating webhooks, an Agent sidecar is automatically injected into any pod created with the label `agent.datadoghq.com/sidecar:fargate`. 
   **The Admission Controller does not mutate pods that are already created**.

**Example result**

The following is a `spec.containers` snippet from a Redis deployment where the Admission Controller injected an Agent sidecar. The sidecar is automatically configured using internal defaults, with additional settings to run in an EKS Fargate environment. The sidecar uses the image repository and tags set in the Helm values. Communication between Cluster Agent and sidecars is enabled by default. 

{{< highlight yaml "hl_lines=7-29" >}}
  containers:
  - args:
    - redis-server
    image: redis:latest
  # ...
  - env:
    - name: DD_API_KEY
      valueFrom:
        secretKeyRef:
          key: api-key
          name: datadog-secret
    - name: DD_CLUSTER_AGENT_AUTH_TOKEN
      valueFrom:
        secretKeyRef:
          key: token
          name: datadog-secret
    - name: DD_EKS_FARGATE
      value: "true"
    # ...
    image: gcr.io/datadoghq/agent:7.51.0
    imagePullPolicy: IfNotPresent
    name: datadog-agent-injected
    resources:
      limits:
        cpu: 200m
        memory: 256Mi
      requests:
        cpu: 200m
        memory: 256Mi
{{< /highlight >}}

###### Sidecar profiles and custom selectors

To further configure the Agent or its container resources, use the Helm property `clusterAgent.admissionController.agentSidecarInjection.profiles` to add environment variable definitions and resource settings. Use the `clusterAgent.admissionController.agentSidecarInjection.selectors` property to configure a custom selector to target workload pods instead of updating the workload to add `agent.datadoghq.com/sidecar:fargate` labels.

1. Create a Helm `datadog-values.yaml` file that configures a sidecar profile and a custom pod selector. 

   **Example**

   In the following example, a selector targets all pods with the label `"app": redis`. The sidecar profile configures a `DD_PROCESS_AGENT_PROCESS_COLLECTION_ENABLED` environment variable and resource settings. 

   ```yaml
   clusterAgent:
     admissionController:
       agentSidecarInjection:
         selectors:
           - objectSelector:
               matchLabels:
                   "app": redis
         profiles:
           - env:
             - name: DD_PROCESS_AGENT_PROCESS_COLLECTION_ENABLED
               value: "true"
             resources:
               requests:
                 cpu: "400m"
                 memory: "256Mi"
               limits:
                 cpu: "800m"
                 memory: "512Mi"
   ```

2. Install the chart:

   ```shell
   helm install datadog datadog/datadog -n datadog-agent \
       --set datadog.clusterName=cluster-name \
       --set agents.enabled=false \
       --set datadog.apiKeyExistingSecret=datadog-secret \
       --set clusterAgent.tokenExistingSecret=datadog-secret \
       --set clusterAgent.admissionController.agentSidecarInjection.enabled=true \
       --set clusterAgent.admissionController.agentSidecarInjection.provider=fargate \
       -f datadog-values.yaml
   ```
   **Note**: Use `agents.enabled=false` for a Fargate-only cluster. On a mixed cluster, set `agents.enabled=true` to create a DaemonSet for monitoring workloads on EC2 instances.

3. After the Cluster Agent reaches a running state and registers Admission Controller mutating webhooks, an Agent sidecar is automatically injected into any pod created with the label `app:redis`. 
   **The Admission Controller does not mutate pods that are already created**.

**Example result**

The following is a `spec.containers` snippet from a Redis deployment where the Admission Controller injected an Agent sidecar. The environment variables and resource settings from `datadog-values.yaml` are automatically applied.

{{< highlight yaml "hl_lines=12-30" >}}
labels:
  app: redis
  eks.amazonaws.com/fargate-profile: fp-fargate
  pod-template-hash: 7b86c456c4
# ...
containers:
- args:
  - redis-server
  image: redis:latest
# ...
- env:
  - name: DD_API_KEY
    valueFrom:
      secretKeyRef:
        key: api-key
        name: datadog-secret
  # ...
  - name: DD_PROCESS_AGENT_PROCESS_COLLECTION_ENABLED
    value: "true"
  # ...
  image: gcr.io/datadoghq/agent:7.51.0
  imagePullPolicy: IfNotPresent
  name: datadog-agent-injected
  resources:
    limits:
      cpu: 800m
      memory: 512Mi
    requests:
      cpu: 400m
      memory: 256Mi
{{< /highlight >}}


<!-- xxz tab xxx -->
<!-- xxx tab "Manual" xxx -->
##### Manual

To start collecting data from your Fargate type pod, deploy the Datadog Agent v7.17+ as a sidecar of your application. This is the minimum configuration required to collect metrics from your application running in the pod, notice the addition of `DD_EKS_FARGATE=true` in the manifest to deploy your Datadog Agent sidecar.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
 name: "<APPLICATION_NAME>"
 namespace: default
spec:
 selector:
   matchLabels:
     app: "<APPLICATION_NAME>"
 replicas: 1
 template:
   metadata:
     labels:
       app: "<APPLICATION_NAME>"
     name: "<POD_NAME>"
   spec:
     serviceAccountName: datadog-agent
     containers:
     - name: "<APPLICATION_NAME>"
       image: "<APPLICATION_IMAGE>"
     ## Running the Agent as a side-car
     - image: datadog/agent
       name: datadog-agent
       env:
       - name: DD_API_KEY
         value: "<YOUR_DATADOG_API_KEY>"
         ## Set DD_SITE to "datadoghq.eu" to send your
         ## Agent data to the Datadog EU site
       - name: DD_SITE
         value: "datadoghq.com"
       - name: DD_EKS_FARGATE
         value: "true"
       - name: DD_CLUSTER_NAME
         value: "<CLUSTER_NAME>"
       - name: DD_KUBERNETES_KUBELET_NODENAME
         valueFrom:
           fieldRef:
             apiVersion: v1
             fieldPath: spec.nodeName
      resources:
          requests:
            memory: "256Mi"
            cpu: "200m"
          limits:
            memory: "256Mi"
            cpu: "200m"
```

**Note**: Don't forget to replace `<YOUR_DATADOG_API_KEY>` with the [Datadog API key from your organization][14].

**Note**: Add your desired `kube_cluster_name:<CLUSTER_NAME>` to the list of `DD_TAGS` to ensure your metrics are tagged by your desired cluster. You can append additional tags here as space separated `<KEY>:<VALUE>` tags. For Agents `7.34+` and `6.34+`, this is not required. Instead, set the `DD_CLUSTER_NAME` environment variable.

###### Running the Cluster Agent or the Cluster Checks Runner

Datadog recommends you run the Cluster Agent to access features such as [events collection][29], [Kubernetes resources view][30], and [cluster checks][31].

When using EKS Fargate, there are two possible scenarios depending on whether or not the EKS cluster is running mixed workloads (Fargate/non-Fargate).

If the EKS cluster runs Fargate and non-Fargate workloads, and you want to monitor the non-Fargate workload through Node Agent DaemonSet, add the Cluster Agent/Cluster Checks Runner to this deployment. For more information, see the [Cluster Agent Setup][25].

The Cluster Agent token must be reachable from the Fargate tasks you want to monitor. If you are using the Helm Chart or Datadog Operator, this is not reachable by default because a secret in the target namespace is created.

You have two options for this to work properly:

* Use an hardcoded token value (`clusterAgent.token` in Helm, `credentials.token` in the Datadog Operator); convenient, but less secure.
* Use a manually-created secret (`clusterAgent.tokenExistingSecret` in Helm, not available in the Datadog Operator) and replicate it in all namespaces where Fargate tasks need to be monitored; secure, but requires extra operations.
**Note**:  The `token` value requires a minimum of 32 characters.

If the EKS cluster runs only Fargate workloads, you need a standalone Cluster Agent deployment. And, as described above, choose one of the two options for making the token reachable.

Use the following Helm `values.yaml`:

```yaml
datadog:
  apiKey: <YOUR_DATADOG_API_KEY>
  clusterName: <CLUSTER_NAME>
agents:
  enabled: false
clusterAgent:
  enabled: true
  replicas: 2
  env:
    - name: DD_EKS_FARGATE
      value: "true"
```


In both cases, you need to change the Datadog Agent sidecar manifest in order to allow communication with the Cluster Agent:

```yaml
       env:
        - name: DD_CLUSTER_AGENT_ENABLED
          value: "true"
        - name: DD_CLUSTER_AGENT_AUTH_TOKEN
          value: <hardcoded token value> # Use valueFrom: if you're using a secret
        - name: DD_CLUSTER_AGENT_URL
          value: https://<CLUSTER_AGENT_SERVICE_NAME>.<CLUSTER_AGENT_SERVICE_NAMESPACE>.svc.cluster.local:5005
        - name: DD_ORCHESTRATOR_EXPLORER_ENABLED # Required to get Kubernetes resources view
          value: "true"
        - name: DD_CLUSTER_NAME
          value: <CLUSTER_NAME>
```

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->


## Cluster performance

For insights into your EKS cluster performance, enable a [Cluster Check Runner][34] to collect metrics from the [`kube-state-metrics`][33] service.

## Metrics collection

### Integration metrics

Use [Autodiscovery labels with your application container][15] to start collecting its metrics for the [supported Agent integrations][16].

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
 name: "<APPLICATION_NAME>"
 namespace: default
spec:
 replicas: 1
 selector:
   matchLabels:
     app: "<APPLICATION_NAME>"
 template:
   metadata:
     labels:
       app: "<APPLICATION_NAME>"
     name: "<POD_NAME>"
     annotations:
      ad.datadoghq.com/<CONTAINER_NAME>.check_names: '[<CHECK_NAME>]'
      ad.datadoghq.com/<CONTAINER_IDENTIFIER>.init_configs: '[<INIT_CONFIG>]'
      ad.datadoghq.com/<CONTAINER_IDENTIFIER>.instances: '[<INSTANCE_CONFIG>]'
   spec:
     serviceAccountName: datadog-agent
     containers:
     - name: "<APPLICATION_NAME>"
       image: "<APPLICATION_IMAGE>"
     ## Running the Agent as a side-car
     - image: datadog/agent
       name: datadog-agent
       env:
       - name: DD_API_KEY
         value: "<YOUR_DATADOG_API_KEY>"
         ## Set DD_SITE to "datadoghq.eu" to send your
         ## Agent data to the Datadog EU site
       - name: DD_SITE
         value: "datadoghq.com"
       - name: DD_EKS_FARGATE
         value: "true"
       - name: DD_KUBERNETES_KUBELET_NODENAME
         valueFrom:
           fieldRef:
             apiVersion: v1
             fieldPath: spec.nodeName
      resources:
          requests:
            memory: "256Mi"
            cpu: "200m"
          limits:
            memory: "256Mi"
            cpu: "200m"
```

**Notes**:

- Don't forget to replace `<YOUR_DATADOG_API_KEY>` with the [Datadog API key from your organization][14].
- Container metrics are not available in Fargate because the `cgroups` volume from the host can't be mounted into the Agent. The [Live Containers][17] view reports 0 for CPU and Memory.

### DogStatsD

Set up the container port `8125` over your Agent container to forward [DogStatsD metrics][18] from your application container to Datadog.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
 name: "<APPLICATION_NAME>"
 namespace: default
spec:
 replicas: 1
 selector:
   matchLabels:
     app: "<APPLICATION_NAME>"
 template:
   metadata:
     labels:
       app: "<APPLICATION_NAME>"
     name: "<POD_NAME>"
   spec:
     serviceAccountName: datadog-agent
     containers:
     - name: "<APPLICATION_NAME>"
       image: "<APPLICATION_IMAGE>"
     ## Running the Agent as a side-car
     - image: datadog/agent
       name: datadog-agent
       ## Enabling port 8125 for DogStatsD metric collection
       ports:
        - containerPort: 8125
          name: dogstatsdport
          protocol: UDP
       env:
       - name: DD_API_KEY
         value: "<YOUR_DATADOG_API_KEY>"
         ## Set DD_SITE to "datadoghq.eu" to send your
         ## Agent data to the Datadog EU site
       - name: DD_SITE
         value: "datadoghq.com"
       - name: DD_EKS_FARGATE
         value: "true"
       - name: DD_KUBERNETES_KUBELET_NODENAME
         valueFrom:
           fieldRef:
             apiVersion: v1
             fieldPath: spec.nodeName
      resources:
          requests:
            memory: "256Mi"
            cpu: "200m"
          limits:
            memory: "256Mi"
            cpu: "200m"
```

**Note**: Don't forget to replace `<YOUR_DATADOG_API_KEY>` with the [Datadog API key from your organization][14].

### Live containers

Datadog Agent v6.19+ supports live containers in the EKS Fargate integration. Live containers appear on the [Containers][19] page.

### Live processes

Datadog Agent v6.19+ supports live processes in the EKS Fargate integration. Live processes appear on the [Processes][20] page. To enable live processes, [enable shareProcessNamespace in the pod spec][21].

### Kubernetes resources view

To collect Kubernetes resource views, you need a [Cluster Agent setup](#running-the-cluster-agent-or-the-cluster-checks-runner).

## Log collection

### Collecting logs from EKS on Fargate with Fluent Bit.

Monitor EKS Fargate logs by using [Fluent Bit][22] to route EKS logs to CloudWatch Logs and the [Datadog Forwarder][23] to route logs to Datadog.

1. To configure Fluent Bit to send logs to CloudWatch, create a Kubernetes ConfigMap that specifies CloudWatch Logs as its output. The ConfigMap specifies the log group, region, prefix string, and whether to automatically create the log group.

   ```yaml
    kind: ConfigMap
    apiVersion: v1
    metadata:
      name: aws-logging
      namespace: aws-observability
    data:
      output.conf: |
        [OUTPUT]
            Name cloudwatch_logs
            Match   *
            region us-east-1
            log_group_name awslogs-https
            log_stream_prefix awslogs-firelens-example
            auto_create_group true
   ```
2. Use the [Datadog Forwarder][23] to collect logs from Cloudwatch and send them to Datadog.

## Traces collection

Set up the container port `8126` over your Agent container to collect traces from your application container. [Read more about how to set up tracing][24].

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
 name: "<APPLICATION_NAME>"
 namespace: default
spec:
 replicas: 1
 selector:
   matchLabels:
     app: "<APPLICATION_NAME>"
 template:
   metadata:
     labels:
       app: "<APPLICATION_NAME>"
     name: "<POD_NAME>"
   spec:
     serviceAccountName: datadog-agent
     ## Putting the agent in the same namespace as the application for origin detection with cgroup v2
     shareProcessNamespace: true
     containers:
     - name: "<APPLICATION_NAME>"
       image: "<APPLICATION_IMAGE>"
     ## Running the Agent as a side-car
     - image: datadog/agent
       name: datadog-agent
       ## Enabling port 8126 for Trace collection
       ports:
        - containerPort: 8126
          name: traceport
          protocol: TCP
       env:
       - name: DD_API_KEY
         value: "<YOUR_DATADOG_API_KEY>"
         ## Set DD_SITE to "datadoghq.eu" to send your
         ## Agent data to the Datadog EU site
       - name: DD_SITE
         value: "datadoghq.com"
       - name: DD_EKS_FARGATE
         value: "true"
       - name: DD_APM_ENABLED
         value: "true"
       - name: DD_KUBERNETES_KUBELET_NODENAME
         valueFrom:
           fieldRef:
             apiVersion: v1
             fieldPath: spec.nodeName
      resources:
          requests:
            memory: "256Mi"
            cpu: "200m"
          limits:
            memory: "256Mi"
            cpu: "200m"
```

**Note**: Don't forget to replace `<YOUR_DATADOG_API_KEY>` with the [Datadog API key from your organization][14].

## Events collection

To collect events from your AWS EKS Fargate API server, run a [Datadog Cluster Agent within your EKS cluster](#running-the-cluster-agent-or-the-cluster-checks-runner) and [Enable Event collection for your Cluster Agent][19].

Optionally, deploy cluster check runners in addition to setting up the Datadog Cluster Agent to enable cluster checks.

**Note**: You can also collect events if you run the Datadog Cluster Agent in a pod in Fargate.

## Process collection

For Agent 6.19+/7.19+, [Process Collection][26] is available. Enable `shareProcessNamespace` on your pod spec to collect all processes running on your Fargate pod. For example:

```
apiVersion: v1
kind: Pod
metadata:
  name: <NAME>
spec:
  shareProcessNamespace: true
...
```

**Note**: CPU and memory metrics are not available.

## Data Collected

### Metrics

The eks_fargate check submits a heartbeat metric `eks.fargate.pods.running` that is tagged by `pod_name` and `virtual_node` so you can keep track of how many pods are running.

### Service Checks

eks_fargate does not include any service checks.

### Events

eks_fargate does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][20].

## Further Reading

Additional helpful documentation, links, and articles:

- [Key metrics for monitoring AWS Fargate][32]
- [How to collect metrics and logs from AWS Fargate workloads][27]
- [AWS Fargate monitoring with Datadog][28]

[1]: http://docs.datadoghq.com/integrations/ecs_fargate/
[2]: http://docs.datadoghq.com/integrations/amazon_eks/
[3]: http://docs.datadoghq.com/integrations/system
[4]: https://docs.datadoghq.com/getting_started/agent/autodiscovery/
[5]: https://docs.aws.amazon.com/eks/latest/userguide/fargate-profile.html
[6]: http://docs.datadoghq.com/integrations/amazon_eks/#setup
[7]: http://docs.datadoghq.com/agent/kubernetes
[8]: http://docs.datadoghq.com/agent/kubernetes/daemonset_setup
[9]: https://app.datadoghq.com/account/settings#integrations/kubernetes
[10]: https://app.datadoghq.com/account/settings#integrations/amazon-web-services
[11]: https://app.datadoghq.com/account/settings#integrations/amazon-eks
[12]: https://app.datadoghq.com/account/settings#integrations/amazon-ec2
[13]: http://docs.datadoghq.com/integrations/kubernetes
[14]: https://app.datadoghq.com/organization-settings/api-keys
[15]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[16]: https://docs.datadoghq.com/integrations/#cat-autodiscovery
[17]: https://app.datadoghq.com/containers
[18]: http://docs.datadoghq.com/tracing/setup
[19]: https://app.datadoghq.com/containers
[20]: https://app.datadoghq.com/process
[21]: https://kubernetes.io/docs/tasks/configure-pod-container/share-process-namespace/
[22]: https://aws.amazon.com/blogs/containers/fluent-bit-for-amazon-eks-on-aws-fargate-is-here/
[23]: https://docs.datadoghq.com/serverless/libraries_integrations/forwarder/
[24]: http://docs.datadoghq.com/tracing/#send-traces-to-datadog
[25]: http://docs.datadoghq.com/agent/cluster_agent/setup/
[26]: https://docs.datadoghq.com/agent/kubernetes/daemonset_setup/?tab=k8sfile#process-collection
[27]: https://www.datadoghq.com/blog/tools-for-collecting-aws-fargate-metrics/
[28]: https://www.datadoghq.com/blog/aws-fargate-monitoring-with-datadog/
[29]: https://docs.datadoghq.com/agent/kubernetes/?tab=helm#event-collection
[30]: https://docs.datadoghq.com/infrastructure/livecontainers/#kubernetes-resources-view
[31]: https://docs.datadoghq.com/agent/cluster_agent/clusterchecks/#overview
[32]: https://www.datadoghq.com/blog/aws-fargate-metrics/
[33]: https://github.com/kubernetes/kube-state-metrics
[34]: https://docs.datadoghq.com/containers/guide/clustercheckrunners
[35]: http://docs.datadoghq.com/agent/cluster_agent
[36]: https://docs.datadoghq.com/containers/cluster_agent/admission_controller/?tab=operator