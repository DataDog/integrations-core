# Agent Check: eks_fargate

## Overview

<div class="alert alert-warning"> This page describes the EKS Fargate integration. For ECS Fargate, see the documentation for Datadog's <a href="http://docs.datadoghq.com/integrations/ecs_fargate">ECS Fargate integration</a>.
</div>

Amazon EKS Fargate is a managed Kubernetes service that automates certain aspects of deployment and maintenance for any standard Kubernetes environment. The EKS Fargate nodes are managed by AWS Fargate and abstracted away from the user.

EKS Fargate pods not run on traditional EKS nodes and EC2 instances. While the Agent does report [system checks][1], like `system.cpu.*` and `system.memory.*`, these are just for the Agent container. In order to collect data from your AWS Fargate pods, run the Agent as a sidecar within *each* of your desired application pods. The pod needs to be deployed with custom RBAC granting permissions to the kubelet for the Agent to get the required information.

The Agent can only monitor the other containers in the same pod as itself. It will also communicate with the Cluster Agent for some of its reporting. Overall the Agent can:

- Report Kubernetes metrics collection from the pod running your application containers and the Agent
- Run [Autodiscovery][2] based Agent integrations against the containers in the same pod
- Collect APM and DogStatsD metrics for containers in the same pod

If you have a mixed cluster of traditional EKS Nodes and Fargate pods, you will manage the traditional Datadog Kubernetes installation with a Helm Chart or Datadog Operator, and then manage your EKS Fargate pods separately.

**Note**: Cloud Network Monitoring (CNM) is not supported for EKS Fargate.

## Prerequisites
### Fargate profile

Create and specify [AWS Fargate Profile][3] that your pods should run with to deploy your pods within EKS Fargate.

If you do not specify a Fargate Profile your pods use classical EC2 machines. To monitor these pods follow the traditional approach of setting up the [Datadog-Amazon EKS integration setup][4] and [Kubernetes Agent setup][5].

### Secret for keys and tokens

Create a Kubernetes secret `datadog-secret` containing your [Datadog API key][7] and a 32 character alphanumeric token for the Cluster Agent. If you are deploying your traditional Datadog installation in one namespace and the Fargate pods in a different namespace, create the secret in *each* Fargate namespace.

For example:
  ```shell
  # Create the secret in the namespace:datadog-agent
  kubectl create secret generic datadog-secret -n datadog-agent \
    --from-literal api-key=<DATADOG_API_KEY> \
    --from-literal token=<CLUSTER_AGENT_TOKEN>

  # Create the secret in the namespace:fargate
  kubectl create secret generic datadog-secret -n fargate \
    --from-literal api-key=<DATADOG_API_KEY> \
    --from-literal token=<CLUSTER_AGENT_TOKEN>
  ```

This token is used for the Agent / Cluster Agent communication. Creating it in advance ensures both the traditional setups and Fargate pod get the same token value (as opposed to letting the Helm Chart or Operator create a random token for you). For more information how this token is used, see the [Cluster Agent Setup][17].

**Note**: You cannot change the name of the secret containing the Datadog API key and Cluster Agent token. It must be `datadog-secret` for the Agent in the sidecar to connect to Datadog when using the automatic injection methods.

### Amazon EKS Fargate RBAC

This process involves creating a `ClusterRole` for the necessary permissions, and binding it to the `ServiceAccount` your pods are using.

Create a `ClusterRole` using the following manifest for to provide the sidecar Agent the necessary permissions:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: datadog-agent-fargate
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
```

After creating this `ClusterRole` create a `ClusterRoleBinding` to attach this to the namespaced `ServiceAccount` that your pods are currently using. The `ClusterRoleBindings` below reference this previously created `ClusterRole`.

If your pods do not currently use a `ServiceAccount` you can create a setup like the following.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: datadog-agent-fargate
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: datadog-agent-fargate
subjects:
  - kind: ServiceAccount
    name: datadog-agent
    namespace: fargate
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: datadog-agent
  namespace: fargate
```

This creates a `ServiceAccount` named `datadog-agent` in the `fargate` namespace that is referenced in the `ClusterRoleBinding`. Adjust this for your desired namespace of your Fargate pods and set this as the `serviceAccountName` in your pod spec.

If you are using multiple `ServiceAccounts` across namespaces this can be updated to your environment like so:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: datadog-agent-fargate
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: datadog-agent-fargate
subjects:
  - kind: ServiceAccount
    name: <SERVICE_ACCOUNT_1>
    namespace: <NAMESPACE_1>
  - kind: ServiceAccount
    name: <SERVICE_ACCOUNT_2>
    namespace: <NAMESPACE_2>
  - kind: ServiceAccount
    name: <SERVICE_ACCOUNT_3>
    namespace: <NAMESPACE_3>
```

See the section below on [Troubleshooting: ServiceAccount Permissions](#serviceaccount-kubelet-permissions) for commands to validate your permission.

## Setup

Be sure to follow the prerequisite steps above for setting up your profile, secrets, and permissions prior to installing the Datadog Agent.

If you have a mixed cluster of the traditional EKS nodes and Fargate pods you may want to first install the traditional [Agent in Kubernetes][5] using the above Secrets. As well as install the Datadog cloud integrations for [AWS][6].


### Installation

To collect data from your applications running in Amazon EKS Fargate over a Fargate node you will run the Agent as a sidecar. This can be done either manually or using the Datadog Admission Controller's automatic injection. This automatic injection requires the Cluster Agent to be running, and will automatically add the Agent sidecar to your desired pods.

Both methods require you to set your RBAC and `serviceAccountName` in your pod manually.

After installation you can further configure the Agent for [Autodiscovery Integrations](#integration-metrics), [DogStatsD metrics](#dogstatsd), [Traces](#traces-collection), and [Process Collection](#process-collection). [Log collection](#log-collection) is supported in EKS Fargate, however is not managed by the Agent.

### Running the Agent as a sidecar

You can run the Agent as a sidecar by using the [Datadog Admission Controller][25] (requires Cluster Agent v7.52+) or with manual sidecar configuration. With the Admission Controller, you can inject an Agent sidecar into every pod that has the label `agent.datadoghq.com/sidecar: fargate`.

With manual configuration, you must modify every workload manifest when adding or changing the Agent sidecar. Datadog recommends you use the Admission Controller.

<!-- xxx tabs xxx -->
<!-- xxx tab "Datadog Operator" xxx -->
### Admission Controller using Datadog Operator

<div class="alert alert-warning">This feature requires Cluster Agent v7.52.0+, Datadog Operator v1.7.0+. </a>.
</div>

If you do not have the Datadog Operator already running see the [Operator install steps here][5].

The setup below configures the Cluster Agent to communicate with the Agent sidecars, allowing access to features such as [event collection][21], [Kubernetes resources view][22], and [cluster checks][23].

#### Standard injection setup

1.  Create a `DatadogAgent` custom resource in the `datadog-agent.yaml` with Admission Controller injection and the fargate provider enabled:

    ```yaml
    apiVersion: datadoghq.com/v2alpha1
    kind: DatadogAgent
    metadata:
      name: datadog
    spec:
      global:
        clusterAgentTokenSecret:
          secretName: datadog-secret
          keyName: token
        credentials:
          apiSecret:
            secretName: datadog-secret
            keyName: api-key
      features:
        admissionController:
          agentSidecarInjection:
            enabled: true
            provider: fargate
    ```
    Then apply the new configuration based on your namespace
  
    ```shell
    kubectl apply -n datadog-agent -f datadog-agent.yaml
    ```

2.  After the Cluster Agent reaches a running state and registers Admission Controller's mutating webhooks add the label `agent.datadoghq.com/sidecar: fargate` to your desired pods (not the parent workload) to trigger the injection of the Datadog Agent sidecar container.

**Note:** The Admission Controller does not mutate pods that are already created, only new pods. Nor does it adjust your `serviceAccountName`, if you have not set the RBAC for this pod the Agent will not connect to Kubernetes.

##### Example standard injection result

The following is output from a sample Redis Deployment's pod where the Admission Controller injected an Agent sidecar. The environment variables and resource settings are automatically applied based on the Datadog Fargate profile's internal default values.

The sidecar uses the image repository and tags set in `datadog-agent.yaml`. Communication between Cluster Agent and sidecars is enabled by default.
  
  {{< highlight yaml "hl_lines=15-37" >}}
  metadata:
    labels:
      app: redis
      eks.amazonaws.com/fargate-profile: fp-fargate
      agent.datadoghq.com/sidecar: fargate
  spec:
    serviceAccountName: datadog-agent
    containers:
    - name: my-redis
      image: redis:latest
      args:
        - redis-server
      # (...)

    - name: datadog-agent-injected
      image: gcr.io/datadoghq/agent:7.64.0
      env:
        - name: DD_API_KEY
          valueFrom:
            secretKeyRef:
              key: api-key
              name: datadog-secret
        - name: DD_EKS_FARGATE
          value: "true"
        - name: DD_CLUSTER_AGENT_AUTH_TOKEN
          valueFrom:
            secretKeyRef:
              key: token
              name: datadog-secret
        # (...)
      resources:
        limits:
          cpu: 200m
          memory: 256Mi
        requests:
          cpu: 200m
          memory: 256Mi
   {{< /highlight >}}

#### Sidecar profiles and custom selectors

To further configure the Agent or its container resources, use the properties in your `DatadogAgent` resource.
- Use the `spec.features.admissionController.agentSidecarInjection.profiles` to add environment variable definitions and resource settings.
- Use the `spec.features.admissionController.agentSidecarInjection.selectors` property to configure a custom selector to target your desired workload pods instead of pods with the `agent.datadoghq.com/sidecar: fargate` label.

You can adjust the profile of the injected Agent container without updating the label selector if desired.

For a full example:

1.  Create a `DatadogAgent` custom resource in `datadog-values.yaml` file that configures a sidecar profile and a custom pod selector.

    In the following example, a selector targets all pods with the label `app: redis`. The new sidecar profile configures a `DD_PROCESS_CONFIG_PROCESS_COLLECTION_ENABLED` environment variable and new resource settings.

    ```yaml
    #(...)
    spec:
      #(...)
      features:
        admissionController:
          agentSidecarInjection:
            enabled: true
            provider: fargate
            selectors:
              - objectSelector:
                  matchLabels:
                    app: redis
            profiles:
              - env:
                - name: DD_PROCESS_CONFIG_PROCESS_COLLECTION_ENABLED
                  value: "true"
                resources:
                  requests:
                    cpu: "400m"
                    memory: "256Mi"
                  limits:
                    cpu: "800m"
                    memory: "512Mi"
    ```

    Then apply the new configuration:
      
    ```shell
    kubectl apply -n datadog-agent -f datadog-agent.yaml
    ```

2.  After the Cluster Agent reaches a running state and registers Admission Controller mutating webhooks, an Agent sidecar is automatically injected into any new pod created with the label `app: redis`. **The Admission Controller does not mutate pods that are already created**.

##### Example custom profile result

The following is output from a Redis Deployment's pod where the Admission Controller injected an Agent sidecar based on the pod label `app: redis` instead of the label `agent.datadoghq.com/sidecar: fargate`.
 
The environment variables and resource settings are automatically applied based on the new Fargate profile configured in the `DatadogAgent`.
     
  {{< highlight yaml "hl_lines=29-38" >}}
  metadata: 
    labels:
      app: redis
      eks.amazonaws.com/fargate-profile: fp-fargate
  spec:
    serviceAccountName: datadog-agent
    containers:
    - name: my-redis
      image: redis:latest
      args:
      - redis-server
      # (...)

    - name: datadog-agent-injected
      image: gcr.io/datadoghq/agent:7.64.0
      env:
        - name: DD_API_KEY
          valueFrom:
            secretKeyRef:
              key: api-key
              name: datadog-secret
        - name: DD_EKS_FARGATE
          value: "true"
        - name: DD_CLUSTER_AGENT_AUTH_TOKEN
          valueFrom:
            secretKeyRef:
              key: token
              name: datadog-secret
        - name: DD_PROCESS_CONFIG_PROCESS_COLLECTION_ENABLED
          value: "true"
        #(...)
      resources:
        requests:
          cpu: "400m"
          memory: "256Mi"
        limits:
          cpu: "800m"
          memory: "512Mi"
  {{< /highlight >}}

<!-- xxz tab xxx -->
<!-- xxx tab "Helm" xxx -->

### Admission Controller using Helm

<div class="alert alert-warning">This feature requires Cluster Agent v7.52.0+.
</div>

The setup below configures the Cluster Agent to communicate with the Agent sidecars, allowing access to features such as [events collection][21], [Kubernetes resources view][22], and [cluster checks][23].

#### Standard injection setup

1.  Create a Helm configuration file `datadog-values.yaml` with Admission Controller injection and the fargate provider enabled:

    ```yaml
    datadog:
      apiKeyExistingSecret: datadog-secret
      clusterName: <CLUSTER_NAME>
    clusterAgent:
      tokenExistingSecret: datadog-secret
      admissionController:
        agentSidecarInjection:
          enabled: true
          provider: fargate
    ```
    
    **Note**: You can set `agents.enabled=false` for a Fargate-only cluster to skip creating the traditional DaemonSet for monitoring workloads on the EC2 instances.

2.  Deploy the chart in your desired namespace:
    
    ```shell
    helm install datadog-agent -f datadog-values.yaml datadog/datadog
    ```

3.  After the Cluster Agent reaches a running state and registers Admission Controller's mutating webhooks add the label `agent.datadoghq.com/sidecar: fargate` to your desired pods (not the parent workload) to trigger the injection of the Datadog Agent sidecar container.

**Note:** The Admission Controller does not mutate pods that are already created, only new pods. Nor does it adjust your `serviceAccountName`, if you have not set the RBAC for this pod the Agent will not connect to Kubernetes.

##### Example standard injection result

The following is output from a sample Redis Deployment's pod where the Admission Controller injected an Agent sidecar. The environment variables and resource settings are automatically applied based on the Datadog Fargate profile's internal default values.

The sidecar uses the image repository and tags set in the Helm values. Communication between Cluster Agent and sidecars is enabled by default.

  {{< highlight yaml "hl_lines=15-37" >}}
  metadata:
    labels:
      app: redis
      eks.amazonaws.com/fargate-profile: fp-fargate
      agent.datadoghq.com/sidecar: fargate
  spec:
    serviceAccountName: datadog-agent
    containers:
    - name: my-redis
      image: redis:latest
      args:
        - redis-server
      # (...)

    - name: datadog-agent-injected
      image: gcr.io/datadoghq/agent:7.64.0
      env:
        - name: DD_API_KEY
          valueFrom:
            secretKeyRef:
              key: api-key
              name: datadog-secret
        - name: DD_EKS_FARGATE
          value: "true"
        - name: DD_CLUSTER_AGENT_AUTH_TOKEN
          valueFrom:
            secretKeyRef:
              key: token
              name: datadog-secret
        # (...)
      resources:
        limits:
          cpu: 200m
          memory: 256Mi
        requests:
          cpu: 200m
          memory: 256Mi
   {{< /highlight >}}

#### Sidecar profiles and custom selectors

To further configure the Agent or its container resources, use the properties in the Helm Chart:

- Use the Helm property `clusterAgent.admissionController.agentSidecarInjection.profiles` to add environment variable definitions and resource settings.
- Use the `clusterAgent.admissionController.agentSidecarInjection.selectors` property to configure a custom selector to target your desired workload pods instead of pods with the `agent.datadoghq.com/sidecar: fargate` label.

You can adjust the profile of the injected Agent container without updating the label selector if desired.

For a full example:

1.  Create a Helm `datadog-values.yaml` file that configures a sidecar profile and a custom pod selector.

    In the following example, a selector targets all pods with the label `app: redis`. The sidecar profile configures a `DD_PROCESS_CONFIG_PROCESS_COLLECTION_ENABLED` environment variable and new resource settings.

    ```yaml
    #(...)
    clusterAgent:
      admissionController:
        agentSidecarInjection:
          enabled: true
          provider: fargate
          selectors:
            - objectSelector:
                matchLabels:
                  app: redis
          profiles:
            - env:
              - name: DD_PROCESS_CONFIG_PROCESS_COLLECTION_ENABLED
                value: "true"
              resources:
                requests:
                  cpu: "400m"
                  memory: "256Mi"
                limits:
                  cpu: "800m"
                  memory: "512Mi"
    ```

2. Upgrade your Helm Chart:

   ```shell
   helm upgrade datadog-agent -f datadog-values.yaml datadog/datadog
   ```

3. After the Cluster Agent reaches a running state and registers Admission Controller mutating webhooks, an Agent sidecar is automatically injected into any pod created with the label `app: redis`.
   **The Admission Controller does not mutate pods that are already created**.

##### Example custom profile result

The following is output from a Redis Deployment's pod where the Admission Controller injected an Agent sidecar based on the pod label `app: redis` instead of the label `agent.datadoghq.com/sidecar: fargate`.

The environment variables and resource settings are automatically applied based on the new Fargate profile configured in the Helm configuration.

  {{< highlight yaml "hl_lines=29-37" >}}
  metadata:
    labels:
      app: redis
      eks.amazonaws.com/fargate-profile: fp-fargate
  spec:
    serviceAccountName: datadog-agent
    containers:
    - name: my-redis
      image: redis:latest
      args:
      - redis-server
      # (...)

    - name: datadog-agent-injected
      image: gcr.io/datadoghq/agent:7.64.0
      env:
        - name: DD_API_KEY
          valueFrom:
            secretKeyRef:
              key: api-key
              name: datadog-secret
        - name: DD_EKS_FARGATE
          value: "true"
        - name: DD_CLUSTER_AGENT_AUTH_TOKEN
          valueFrom:
            secretKeyRef:
              key: token
              name: datadog-secret
        - name: DD_PROCESS_CONFIG_PROCESS_COLLECTION_ENABLED
          value: "true"
        #(...)
      resources:
        requests:
          cpu: "400m"
          memory: "256Mi"
        limits:
          cpu: "800m"
          memory: "512Mi"
  {{< /highlight >}}


<!-- xxz tab xxx -->
<!-- xxx tab "Manual" xxx -->
### Manual

To start collecting data from your Fargate type pod, deploy the Datadog Agent v7.17+ as a sidecar container within your application's pod. This is the minimum configuration required to collect metrics from your application running in the pod, notice the addition of `DD_EKS_FARGATE=true` in the manifest to deploy your Datadog Agent sidecar.

Replace the placeholder value `<DATADOG_SITE>` to your site: {{< region-param key="dd_site" code="true" >}}. Defaults to `datadoghq.com`. As well as ensure you are using a `serviceAccountName` with the prerequisite permissions.

This uses the Secret `datadog-secret` for the API Key created in the prerequisite steps.

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
    spec:
      serviceAccountName: datadog-agent
      containers:
        # Your original container
        - name: "<APPLICATION_NAME>"
          image: "<APPLICATION_IMAGE>"

        # Running the Agent as a side-car
        - name: datadog-agent
          image: gcr.io/datadoghq/agent:7
          env:
            - name: DD_API_KEY
              valueFrom:
                secretKeyRef:
                  key: api-key
                  name: datadog-secret
            - name: DD_SITE
              value: "<DATADOG_SITE>"
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

**Note**: Add `DD_TAGS` to append additional space separated `<KEY>:<VALUE>` tags. The `DD_CLUSTER_NAME` environment variable will set your `kube_cluster_name` tag.

#### Running the Cluster Agent or the Cluster Checks Runner

Datadog recommends you run the Cluster Agent to access features such as [events collection][21], [Kubernetes resources view][22], and [cluster checks][23].

When using EKS Fargate, there are two possible scenarios depending on whether or not the EKS cluster is running mixed workloads (Fargate/non-Fargate).

If the EKS cluster runs Fargate and non-Fargate workloads, and you want to monitor the non-Fargate workload through Node Agent DaemonSet, add the Cluster Agent/Cluster Checks Runner to this deployment. For more information, see the [Cluster Agent Setup][17].

When deploying your Cluster Agent use the Secret and token created in the prerequisite steps.

##### Helm
```yaml
datadog:
  apiKeyExistingSecret: datadog-secret
  clusterName: <CLUSTER_NAME>
clusterAgent:
  tokenExistingSecret: datadog-secret
```

Set `agents.enabled=false` if you are not using standard non-Fargate workloads.

##### Operator
```yaml
apiVersion: datadoghq.com/v2alpha1
kind: DatadogAgent
metadata:
  name: datadog
spec:
  global:
    clusterAgentTokenSecret:
      secretName: datadog-secret
      keyName: token
    credentials:
      apiSecret:
        secretName: datadog-secret
        keyName: api-key
```

##### Configuring sidecar for Cluster Agent
In both cases, you need to change the Datadog Agent sidecar manifest in order to allow communication with the Cluster Agent:

```yaml
    containers:
    #(...)
    - name: datadog-agent
      image: gcr.io/datadoghq/agent:7
      env:
        #(...)
        - name: DD_CLUSTER_NAME
          value: <CLUSTER_NAME>
        - name: DD_CLUSTER_AGENT_ENABLED
          value: "true"
        - name: DD_CLUSTER_AGENT_AUTH_TOKEN
          valueFrom:
            secretKeyRef:
              name: datadog-secret
              key: token
        - name: DD_CLUSTER_AGENT_URL
          value: https://<CLUSTER_AGENT_SERVICE_NAME>.<CLUSTER_AGENT_SERVICE_NAMESPACE>.svc.cluster.local:5005
```

Se the `DD_CLUSTER_AGENT_URL` relative to the Service name and Namespace created for your Datadog Cluster Agent.

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

## Metrics collection

### Integration metrics

Use [Autodiscovery annotations with your application container][8] to start collecting its metrics for the [supported Agent integrations][9].

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
      annotations:
        ad.datadoghq.com/<CONTAINER_NAME>.checks: |
          {
            "<INTEGRATION_NAME>": {
              "init_config": <INIT_CONFIG>,
              "instances": [<INSTANCES_CONFIG>]
            }
          }
    spec:
      serviceAccountName: datadog-agent
      containers:
      # Your original container
      - name: "<CONTAINER_NAME>"
        image: "<CONTAINER_IMAGE>"

      # Running the Agent as a side-car
      - name: datadog-agent
        image: gcr.io/datadoghq/agent:7
        env:
          - name: DD_API_KEY
            valueFrom:
              secretKeyRef:
                key: api-key
                name: datadog-secret
          - name: DD_SITE
            value: "<DATADOG_SITE>"
          - name: DD_EKS_FARGATE
            value: "true"
          - name: DD_KUBERNETES_KUBELET_NODENAME
            valueFrom:
              fieldRef:
                apiVersion: v1
                fieldPath: spec.nodeName
          # (...)
```

### DogStatsD

Set up the container port `8125` over your Agent container to forward [DogStatsD metrics][10] from your application container to Datadog.

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
    spec:
      serviceAccountName: datadog-agent
      containers:
      # Your original container
      - name: "<CONTAINER_NAME>"
        image: "<CONTAINER_IMAGE>"

      # Running the Agent as a side-car
      - name: datadog-agent
        image: gcr.io/datadoghq/agent:7
        ports:
          - name: dogstatsdport
            containerPort: 8125
            protocol: UDP
        env:
          - name: DD_API_KEY
            valueFrom:
              secretKeyRef:
                key: api-key
                name: datadog-secret
          - name: DD_SITE
            value: "<DATADOG_SITE>"
          - name: DD_EKS_FARGATE
            value: "true"
          - name: DD_KUBERNETES_KUBELET_NODENAME
            valueFrom:
              fieldRef:
                apiVersion: v1
                fieldPath: spec.nodeName
          # (...)

```

### Live containers

Datadog Agent v6.19+ supports live containers in the EKS Fargate integration. Live containers appear on the [Containers][11] page.

### Kubernetes resources view

To collect Kubernetes resource views, you need a [Cluster Agent setup][17] and a valid connection between the sidecar Agent and Cluster Agent. This is connected for you automatically if you are using the sidecar injection setup.

When configuring manually ensure you are [connecting the sidecar Agent](#configuring-sidecar-for-cluster-agent).

## Process collection

For Agent 6.19+/7.19+, [Process Collection][18] is available. Set the Agent environment variable `DD_PROCESS_CONFIG_PROCESS_COLLECTION_ENABLED=true` and [set `shareProcessNamespace: true` on your pod spec][13] to collect all processes running on your Fargate pod.

For example:

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
    spec:
      serviceAccountName: datadog-agent
      shareProcessNamespace: true
      containers:
      # Your original container
      - name: "<CONTAINER_NAME>"
        image: "<CONTAINER_IMAGE>"

      # Running the Agent as a side-car
      - name: datadog-agent
        image: gcr.io/datadoghq/agent:7
        env:
          - name: DD_API_KEY
            valueFrom:
              secretKeyRef:
                key: api-key
                name: datadog-secret
          - name: DD_SITE
            value: "<DATADOG_SITE>"
          - name: DD_EKS_FARGATE
            value: "true"
          - name: DD_KUBERNETES_KUBELET_NODENAME
            valueFrom:
              fieldRef:
                apiVersion: v1
                fieldPath: spec.nodeName
          - name: DD_PROCESS_CONFIG_PROCESS_COLLECTION_ENABLED
            value: "true"
          # (...)
```

## Log collection

### Collecting logs from EKS on Fargate with Fluent Bit.

Monitor EKS Fargate logs by using [Fluent Bit][14] to route EKS logs to CloudWatch Logs and the [Datadog Forwarder][15] to route logs to Datadog.

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
2. Use the [Datadog Forwarder][15] to collect logs from Cloudwatch and send them to Datadog.

## Traces collection

Set up the container port `8126` over your Agent container to collect traces from your application container. As well as set the [`shareProcessNamespace: true` in the pod spec][13] to assist the Agent for origin detection.

[Read more about how to set up tracing][16].

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
    spec:
      serviceAccountName: datadog-agent
      shareProcessNamespace: true
      containers:
      # Your original container
      - name: "<CONTAINER_NAME>"
        image: "<CONTAINER_IMAGE>"

      # Running the Agent as a side-car
      - name: datadog-agent
        image: gcr.io/datadoghq/agent:7
        ports:
          - name: traceport
            containerPort: 8126
            protocol: TCP
        env:
          - name: DD_API_KEY
            valueFrom:
              secretKeyRef:
                key: api-key
                name: datadog-secret
          - name: DD_SITE
            value: "<DATADOG_SITE>"
          - name: DD_EKS_FARGATE
            value: "true"
          - name: DD_KUBERNETES_KUBELET_NODENAME
            valueFrom:
              fieldRef:
                apiVersion: v1
                fieldPath: spec.nodeName
          # (...)
```

In EKS Fargate you do not have to set the `DD_AGENT_HOST` address in your application container. Let this default to `localhost`.

## Events collection

To collect events from your Amazon EKS Fargate API server, run the [Datadog Cluster Agent][17] within your EKS cluster. The Cluster Agent collects Kubernetes events, including those for the EKS Fargate pods, by default.

**Note**: You can also collect events if you run the Datadog Cluster Agent in a pod in Fargate.

## Data Collected

### Metrics

The `eks_fargate` check submits a heartbeat metric `eks.fargate.pods.running` that is tagged by `pod_name` and `virtual_node` so you can keep track of how many pods are running.

### Service Checks

The `eks_fargate` check does not include any service checks.

### Events

The `eks_fargate` check does not include any events.

## Troubleshooting

### ServiceAccount Kubelet permissions

Ensure you have the right permissions on the `ServiceAccount` associated with your pod. If your pod does not have a `ServiceAccount` associated with it, or, it isn't bound to the correct ClusterRole it won't have access to Kubelet.

This access can be validated with a command like:

```shell
kubectl auth can-i get nodes/pods --as system:serviceaccount:<NAMESPACE>:<SERVICEACCOUNT>
```

For example if your Fargate pod is in the `fargate` namespace with the ServiceAccount `datadog-agent`:
```shell
kubectl auth can-i get nodes/pods --as system:serviceaccount:fargate:datadog-agent
```

This will return `yes` or `no` based on the access.


### Datadog Agent Container Security Context

The Datadog Agent container is designed to run as the dd-agent user (UID: 100). If you override the default security context by setting, for example, `runAsUser: 1000` in your pod spec, the container fails to start due to insufficient permissions. You may see errors such as:

```log
[s6-init] making user provided files available at /var/run/s6/etc...exited 0.
s6-chown: fatal: unable to chown /var/run/s6/etc/cont-init.d/50-ecs.sh: Operation not permitted
s6-chown: fatal: unable to chown /var/run/s6/etc/cont-init.d/50-eks.sh: Operation not permitted
s6-chown: fatal: unable to chown /var/run/s6/etc/cont-init.d/60-network-check.sh: Operation not permitted
s6-chown: fatal: unable to chown /var/run/s6/etc/cont-init.d/59-defaults.sh: Operation not permitted
s6-chown: fatal: unable to chown /var/run/s6/etc/cont-init.d/60-sysprobe-check.sh: Operation not permitted
s6-chown: fatal: unable to chown /var/run/s6/etc/cont-init.d/50-ci.sh: Operation not permitted
s6-chown: fatal: unable to chown /var/run/s6/etc/cont-init.d/89-copy-customfiles.sh: Operation not permitted
s6-chown: fatal: unable to chown /var/run/s6/etc/cont-init.d/01-check-apikey.sh: Operation not permitted
s6-chown: fatal: unable to chown /var/run/s6/etc/cont-init.d/51-docker.sh: Operation not permitted
s6-chown: fatal: unable to chown /var/run/s6/etc/cont-init.d/50-kubernetes.sh: Operation not permitted
s6-chown: fatal: unable to chown /var/run/s6/etc/cont-init.d/50-mesos.sh: Operation not permitted
s6-chown: fatal: unable to chown /var/run/s6/etc/services.d/trace/run: Operation not permitted
s6-chown: fatal: unable to chown /var/run/s6/etc/services.d/security/run: Operation not permitted
s6-chown: fatal: unable to chown /var/run/s6/etc/services.d/sysprobe/run: Operation not permitted
s6-chown: fatal: unable to chown /var/run/s6/etc/services.d/agent/run: Operation not permitted
s6-chown: fatal: unable to chown /var/run/s6/etc/services.d/process/run: Operation not permitted
s6-chown: fatal: unable to chown /var/run/s6/etc/services.d/security/finish: Operation not permitted
s6-chown: fatal: unable to chown /var/run/s6/etc/services.d/trace/finish: Operation not permitted
s6-chown: fatal: unable to chown /var/run/s6/etc/services.d/sysprobe/finish: Operation not permitted
s6-chown: fatal: unable to chown /var/run/s6/etc/services.d/agent/finish: Operation not permitted
s6-chown: fatal: unable to chown /var/run/s6/etc/services.d/process/finish: Operation not permitted
[s6-init] ensuring user provided files have correct perms...exited 0.
[fix-attrs.d] applying ownership & permissions fixes...
[fix-attrs.d] done.
[cont-init.d] executing container initialization scripts...
[cont-init.d] 01-check-apikey.sh: executing... 
[cont-init.d] 01-check-apikey.sh: exited 0.
[cont-init.d] 50-ci.sh: executing... 
[cont-init.d] 50-ci.sh: exited 0.
[cont-init.d] 50-ecs.sh: executing... 
[cont-init.d] 50-ecs.sh: exited 0.
[cont-init.d] 50-eks.sh: executing... 
ln: failed to create symbolic link '/etc/datadog-agent/datadog.yaml': Permission denied
[cont-init.d] 50-eks.sh: exited 0.
[cont-init.d] 50-kubernetes.sh: executing... 
[cont-init.d] 50-kubernetes.sh: exited 0.
[cont-init.d] 50-mesos.sh: executing... 
[cont-init.d] 50-mesos.sh: exited 0.
[cont-init.d] 51-docker.sh: executing... 
[cont-init.d] 51-docker.sh: exited 0.
[cont-init.d] 59-defaults.sh: executing... 
touch: cannot touch '/etc/datadog-agent/datadog.yaml': Permission denied
[cont-init.d] 59-defaults.sh: exited 1.
```

Since Datadog Cluster Agent v7.62+, overriding the security context for the Datadog Agent sidecar allows you to maintain consistent security standards across your Kubernetes deployments. Whether using the DatadogAgent custom resource or Helm values, you can ensure that the Agent container runs with the appropriate user, dd-agent (UID 100), as needed by your environment.

By following the examples, you can deploy the Agent sidecar in environments where the default Pod security context must be overridden.

Datadog Operator

```yaml
apiVersion: datadoghq.com/v2alpha1
kind: DatadogAgent
metadata:
  name: datadog
spec:
  features:
    admissionController:
      agentSidecarInjection:
        enabled: true
        provider: fargate
        - securityContext:
            runAsUser: 100
```

Helm

```yaml
clusterAgent:
  admissionController:
    agentSidecarInjection:
      profiles:
        - securityContext:
            runAsUser: 100
```

Need help? Contact [Datadog support][12].

## Further Reading

Additional helpful documentation, links, and articles:

- [Key metrics for monitoring AWS Fargate][24]
- [How to collect metrics and logs from AWS Fargate workloads][19]
- [AWS Fargate monitoring with Datadog][20]

[1]: http://docs.datadoghq.com/integrations/system
[2]: https://docs.datadoghq.com/getting_started/agent/autodiscovery/
[3]: https://docs.aws.amazon.com/eks/latest/userguide/fargate-profile.html
[4]: http://docs.datadoghq.com/integrations/amazon_eks/#setup
[5]: http://docs.datadoghq.com/agent/kubernetes/installation
[6]: /account/settings#integrations/amazon-web-services
[7]: /organization-settings/api-keys
[8]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[9]: https://github.com/DataDog/integrations-core
[10]: https://docs.datadoghq.com/developers/dogstatsd/
[11]: /containers
[12]: https://docs.datadoghq.com/help/
[13]: https://kubernetes.io/docs/tasks/configure-pod-container/share-process-namespace/
[14]: https://aws.amazon.com/blogs/containers/fluent-bit-for-amazon-eks-on-aws-fargate-is-here/
[15]: https://docs.datadoghq.com/serverless/libraries_integrations/forwarder/
[16]: http://docs.datadoghq.com/tracing/#send-traces-to-datadog
[17]: http://docs.datadoghq.com/agent/cluster_agent/setup/
[18]: https://docs.datadoghq.com/infrastructure/process/?tab=kubernetesmanual#installation
[19]: https://www.datadoghq.com/blog/tools-for-collecting-aws-fargate-metrics/
[20]: https://www.datadoghq.com/blog/aws-fargate-monitoring-with-datadog/
[21]: https://docs.datadoghq.com/containers/kubernetes/configuration/#enable-kubernetes-event-collection
[22]: https://docs.datadoghq.com/infrastructure/containers/orchestrator_explorer
[23]: https://docs.datadoghq.com/agent/cluster_agent/clusterchecks/#overview
[24]: https://www.datadoghq.com/blog/aws-fargate-metrics/
[25]: https://docs.datadoghq.com/containers/cluster_agent/admission_controller/?tab=operator
