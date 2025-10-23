# Agent Check: eks_fargate

## Overview

<div class="alert alert-warning"> This page describes the EKS Fargate integration. For ECS Fargate, see the documentation for Datadog's <a href="http://docs.datadoghq.com/integrations/ecs_fargate">ECS Fargate integration</a>.
</div>

Amazon EKS Fargate is a managed Kubernetes service that automates certain aspects of deployment and maintenance for any standard Kubernetes environment. The EKS Fargate nodes are managed by AWS Fargate and abstracted away from the user.

### How Datadog monitors EKS Fargate pods

EKS Fargate pods do not run on traditional EKS nodes backed by EC2 instances. While the Agent does report [system checks][1], like `system.cpu.*` and `system.memory.*`, these are just for the Agent container. To collect data from your EKS Fargate pods, run the Agent as a sidecar within *each* of your desired application pods. Each pod needs a custom RBAC that grants permissions to the kubelet for the Agent to get the required information.

The Agent sidecar is responsible for monitoring the other containers in the same pod as itself, in addition to communicating with the Cluster Agent for portions of its reporting. The Agent can:

- Report Kubernetes metrics collection from the pod running your application containers and the Agent
- Run [Autodiscovery][2]-based Agent integrations against the containers in the same pod
- Collect APM and DogStatsD metrics for containers in the same pod

If you have a mixed cluster of traditional EKS nodes and Fargate pods, you can manage the EKS nodes with the [standard Datadog Kubernetes installation][5] (Helm chart or Datadog Operator) - and manage the Fargate pods separately.

**Note**: Cloud Network Monitoring (CNM) is not supported for EKS Fargate.

**Minimum Agent version:** 7.18.0

## Setup

### Prerequisites

- An [AWS Fargate profile](#aws-fargate-profile)
- A [Kubernetes Secret named `datadog-secret`](#secret-for-keys-and-tokens), containing your Datadog API key and Cluster Agent token
- An [AWS Fargate RBAC](#aws-fargate-rbac)

#### AWS Fargate profile

Create and specify an [AWS Fargate profile][3] for your EKS Fargate pods.

If you do not specify an AWS Fargate profile, your pods use classical EC2 machines. To monitor these pods, use the [standard Datadog Kubernetes installation][5] with the [Datadog-Amazon EKS integration][4].

#### Secret for keys and tokens

Create a [Kubernetes Secret][26] named `datadog-secret` that contains:
- Your [Datadog API key][7]
- A 32-character alphanumeric token for the Cluster Agent. The Agent and Cluster Agent use this token to communicate. Creating it in advance ensures both the traditional setups and Fargate pod get the same token value (as opposed to letting the Datadog Operator or Helm create a random token for you). For more information on how this token is used, see the [Cluster Agent Setup][17].

```shell
kubectl create secret generic datadog-secret -n <NAMESPACE> \
  --from-literal api-key=<DATADOG_API_KEY> \
  --from-literal token=<CLUSTER_AGENT_TOKEN>
```

If you are deploying your traditional Datadog installation in one namespace and the Fargate pods in a different namespace, create a secret in *both* namespaces:

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

**Note**: To use the Admission Controller to run the Datadog Agent in Fargate, the name of this Kubernetes Secret _must_ be `datadog-secret`.

#### AWS Fargate RBAC

Create a `ClusterRole` for the necessary permissions and bind it to the `ServiceAccount` your pods are using:

1. Create a `ClusterRole` using the following manifest:

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

2. Create a `ClusterRoleBinding` to attach this to the namespaced `ServiceAccount` that your pods are currently using. The `ClusterRoleBindings` below reference this previously created `ClusterRole`.

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
       name: <SERVICE_ACCOUNT>
       namespace: <NAMESPACE>
   ```
   
   #### If your pods do not use a ServiceAccount

   If your pods do not use a `ServiceAccount`, use the following:

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

   This creates a `ServiceAccount` named `datadog-agent` in the `fargate` namespace that is referenced in the `ClusterRoleBinding`. Adjust this for your Fargate pods' namespace and set this as the `serviceAccountName` in your pod spec.

   #### If you are using multiple ServiceAccounts across namespaces
   If you are using multiple `ServiceAccounts` across namespaces for your Fargate pods, use the following:

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

To validate your RBAC, see [Troubleshooting: ServiceAccount Permissions](#serviceaccount-kubelet-permissions).

### Installation

After you complete all prerequisites, run the Datadog Agent as a sidecar container within each of your pods. You can do this with the [Datadog Admission Controller][25]'s automatic injection feature, or manually.

The Admission Controller is a Datadog component that can automatically add the Agent sidecar to every pod that has the label `agent.datadoghq.com/sidecar: fargate`.

Manual configuration requires that you modify every workload manifest when adding or changing the Agent sidecar. Datadog recommends that you use the Admission Controller instead.

**Note**: If you have a mixed cluster of traditional EKS nodes and Fargate pods, set up up monitoring for your traditional nodes with the [standard Datadog Kubernetes installation][5] (with the Kubernetes Secret from the prerequisites) and install the [Datadog-AWS integration][6] and [Datadog-EKS integration][4]. Then, to monitor your Fargate pods, continue with this section.

<!-- xxx tabs xxx -->
<!-- xxx tab "Admission Controller - Datadog Operator" xxx -->
#### Admission Controller - Datadog Operator

1. If you haven't already, [install Helm][27] on your machine.

2. Install the Datadog Operator:
   ```shell
   helm repo add datadog https://helm.datadoghq.com
   helm install datadog-operator datadog/datadog-operator
   ```

3. Create a `datadog-agent.yaml` file to define a `DatadogAgent` custom resource, with Admission Controller and Fargate injection enabled:

    ```yaml
    apiVersion: datadoghq.com/v2alpha1
    kind: DatadogAgent
    metadata:
      name: datadog
    spec:
      global:
        clusterName: <CLUSTER_NAME>
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
4. Apply this configuration:
  
    ```shell
    kubectl apply -n <NAMESPACE> -f datadog-agent.yaml
    ```

5.  After the Cluster Agent reaches a running state and registers Admission Controller's mutating webhooks, add the label `agent.datadoghq.com/sidecar: fargate` to your desired pods (not the parent workload) to trigger the injection of the Datadog Agent sidecar container.

**Note**: The Admission Controller only mutates new pods, not pods that are already created. It does not adjust your `serviceAccountName`. If you have not set the RBAC for this pod, the Agent cannot connect to Kubernetes.

**Example**

The following is output from a sample Redis deployment's pod where the Admission Controller injected an Agent sidecar. The environment variables and resource settings are automatically applied based on the Datadog Fargate profile's internal default values.

The sidecar uses the image repository and tags set in `datadog-agent.yaml`.
  
```yaml
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
```

##### Custom configuration with sidecar profiles and custom selectors - Datadog Operator

To further configure the Agent or its container resources, use the following properties in your `DatadogAgent` resource:

- `spec.features.admissionController.agentSidecarInjection.profiles`, to add environment variable definitions and resource settings
- `spec.features.admissionController.agentSidecarInjection.selectors`, to configure a custom selector to target your desired workload pods (instead of pods with the `agent.datadoghq.com/sidecar: fargate` label)

You can adjust the profile of the injected Agent container without updating the label selector if desired.

For example, the following `datadog-agent.yaml` uses a selector to target all pods with the label `app: redis`. The sidecar profile configures a `DD_PROCESS_CONFIG_PROCESS_COLLECTION_ENABLED` environment variable and new resource settings.

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

Apply this configuration and wait for the Cluster Agent to reach a running state and register Admission Controller mutating webhooks. Then, an Agent sidecar is automatically injected into any new pod created with the label `app: redis`. 

**Note**: The Admission Controller does not mutate pods that are already created.

The following is output from a Redis deployment's pod where the Admission Controller injected an Agent sidecar based on the pod label `app: redis` instead of the label `agent.datadoghq.com/sidecar: fargate`:

```yaml
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
```

The environment variables and resource settings are automatically applied based on the new Fargate profile configured in the `DatadogAgent`.

<!-- xxz tab xxx -->
<!-- xxx tab "Admission Controller - Helm" xxx -->

#### Admission Controller - Helm

1. If you haven't already, [install Helm][27] on your machine.

2. Add the Datadog Helm repository:

   ```shell
   helm repo add datadog https://helm.datadoghq.com
   helm repo update
   ```

3.  Create a `datadog-values.yaml` with Admission Controller and Fargate injection enabled:

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

4.  Deploy the chart in your desired namespace:
    
    ```shell
    helm install datadog-agent -f datadog-values.yaml datadog/datadog
    ```

5.  After the Cluster Agent reaches a running state and registers Admission Controller's mutating webhooks, add the label `agent.datadoghq.com/sidecar: fargate` to your desired pods (not the parent workload) to trigger the injection of the Datadog Agent sidecar container.

**Note**: The Admission Controller only mutates new pods, not pods that are already created. It does not adjust your `serviceAccountName`. If you have not set the RBAC for this pod, the Agent cannot connect to Kubernetes.

On a Fargate-only cluster, you can set `agents.enabled=false` to skip creating the traditional DaemonSet for monitoring workloads on EC2 instances.

**Example**

The following is output from a sample Redis Deployment's pod where the Admission Controller injected an Agent sidecar. The environment variables and resource settings are automatically applied based on the Datadog Fargate profile's internal default values.

The sidecar uses the image repository and tags set in `datadog-values.yaml`.

```yaml
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
```

##### Custom configuration with sidecar profiles and custom selectors - Helm

To further configure the Agent or its container resources, use the following properties in your Helm configuration:

- `clusterAgent.admissionController.agentSidecarInjection.profiles`, to add environment variable definitions and resource settings
- `clusterAgent.admissionController.agentSidecarInjection.selectors`, to configure a custom selector to target your desired workload pods (instead of pods with the `agent.datadoghq.com/sidecar: fargate` label)

You can adjust the profile of the injected Agent container without updating the label selector if desired.

For example, the following `datadog-values.yaml` uses a selector to target all pods with the label `app: redis`. The sidecar profile configures a `DD_PROCESS_CONFIG_PROCESS_COLLECTION_ENABLED` environment variable and new resource settings.

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

Apply this configuration and wait for the Cluster Agent to reach a running state and register Admission Controller mutating webhooks. Then, an Agent sidecar is automatically injected into any new pod created with the label `app: redis`. 

**Note**: The Admission Controller does not mutate pods that are already created.

The following is output from a Redis deployment's pod where the Admission Controller injected an Agent sidecar based on the pod label `app: redis` instead of the label `agent.datadoghq.com/sidecar: fargate`:

```yaml
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
```

The environment variables and resource settings are automatically applied based on the new Fargate profile configured in the Helm configuration.

<!-- xxz tab xxx -->
<!-- xxx tab "Manual" xxx -->
#### Manual

To start collecting data from your Fargate type pod, deploy the Datadog Agent v7.17+ as a sidecar container within your application's pod using the following manifest:

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

        # Running the Agent as a sidecar
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

- Replace `<DATADOG_SITE>` to your site: {{< region-param key="dd_site" code="true" >}}. Defaults to `datadoghq.com`.
- Ensure you are using a `serviceAccountName` with the prerequisite permissions.
- Add `DD_TAGS` to append additional space separated `<KEY>:<VALUE>` tags. The `DD_CLUSTER_NAME` environment variable sets your `kube_cluster_name` tag.

This manifest uses the Secret `datadog-secret` created in the prerequisite steps.

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

Set `agents.enabled=false` to disable the standard node Agent if you are using *only* Fargate workloads.

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

See the `DD_CLUSTER_AGENT_URL` relative to the Service name and Namespace created for your Datadog Cluster Agent.

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

      # Running the Agent as a sidecar
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

In EKS Fargate your application container will send the [DogStatsD metrics][10] to the Datadog Agent sidecar container. The Agent accepts these metrics by default over the port `8125`.

You do not have to set the `DD_AGENT_HOST` address in your application container when sending these metrics. Let this default to `localhost`.


### Live containers

Datadog Agent v6.19+ supports live containers in the EKS Fargate integration. Live containers appear on the [Containers][11] page.

### Kubernetes resources view

To collect Kubernetes resource views, you need a [Cluster Agent setup][17] and a valid connection between the sidecar Agent and Cluster Agent. When using the Admission Controller's sidecar injection setup this is connected for you automatically. When configuring the sidecar manually ensure you are [connecting the sidecar Agent](#configuring-sidecar-for-cluster-agent).

## Process collection

<!-- xxx tabs xxx -->
<!-- xxx tab "Admission Controller - Datadog Operator" xxx -->

To collect all processes running on your Fargate pod:

1. [Set `shareProcessNamespace: true` on your pod spec][13]. For example:

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
           agent.datadoghq.com/sidecar: fargate
       spec:
         serviceAccountName: datadog-agent
         shareProcessNamespace: true
         containers:
         # Your original container
         - name: "<CONTAINER_NAME>"
           image: "<CONTAINER_IMAGE>"
   ```

2. Set the Agent environment variable `DD_PROCESS_CONFIG_PROCESS_COLLECTION_ENABLED=true` by adding a [custom sidecar profile in your Operator's `DatadogAgent` configuration](#custom-configuration-with-sidecar-profiles-and-custom-selectors---datadog-operator):

   ```yaml
   #(...)
   spec:
     #(...)
     features:
       admissionController:
         agentSidecarInjection:
           enabled: true
           provider: fargate
           profiles:
             - env:
               - name: DD_PROCESS_CONFIG_PROCESS_COLLECTION_ENABLED
                 value: "true"
   ```

<!-- xxz tab xxx -->

<!-- xxx tab "Admission Controller - Helm" xxx -->

To collect all processes running on your Fargate pod:

1. [Set `shareProcessNamespace: true` on your pod spec][13]. For example:

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
           agent.datadoghq.com/sidecar: fargate
       spec:
         serviceAccountName: datadog-agent
         shareProcessNamespace: true
         containers:
         # Your original container
         - name: "<CONTAINER_NAME>"
           image: "<CONTAINER_IMAGE>"
   ```
   
2. Set the Agent environment variable `DD_PROCESS_CONFIG_PROCESS_COLLECTION_ENABLED=true` by adding a [custom sidecar profile in your Helm configuration](#custom-configuration-with-sidecar-profiles-and-custom-selectors---helm):

   ```yaml
   clusterAgent:
     admissionController:
       agentSidecarInjection:
         enabled: true
         provider: fargate
         profiles:
           - env:
             - name: DD_PROCESS_CONFIG_PROCESS_COLLECTION_ENABLED
               value: "true"
   ```
<!-- xxz tab xxx -->
<!-- xxx tab "Manual" xxx -->

To collect all processes running on your Fargate pod, set the Agent environment variable `DD_PROCESS_CONFIG_PROCESS_COLLECTION_ENABLED=true` and [set `shareProcessNamespace: true` on your pod spec][13].

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

      # Running the Agent as a sidecar
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

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->


## Log collection

### Collecting logs from EKS on Fargate natively with the Agent

**Minimum Agent version:** 7.71.0

Monitor EKS Fargate logs using the Datadog Agent to collect logs from the kubelet and ship them to Datadog.

1. The most convenient way to enable native kubelet logging is through the Cluster Agent's Admission Controller sidecar injection feature. When configured, all subsequent injected Agent containers automatically have kubelet logging enabled. This feature can also be configured manually in your Application's manifest.

  <!-- xxx tabs xxx -->
  <!-- xxx tab "Admission Controller - Datadog Operator" xxx -->

  Set the `DD_ADMISSION_CONTROLLER_AGENT_SIDECAR_KUBELET_API_LOGGING_ENABLED` Cluster Agent environment variable to `true`, so newly injected Agent containers will have kubelet logging enabled.

  ```yaml
  apiVersion: datadoghq.com/v2alpha1
  kind: DatadogAgent
  metadata:
    name: datadog
    namespace: datadog
  spec:
    features:
      admissionController:
        agentSidecarInjection:
          enabled: true
          provider: fargate
    override:
      clusterAgent:
        env:
          - name: DD_ADMISSION_CONTROLLER_AGENT_SIDECAR_KUBELET_API_LOGGING_ENABLED
            value: "true"
  ```

  <!-- xxz tab xxx -->
  <!-- xxx tab "Admission Controller - Helm" xxx -->

  Set the `DD_ADMISSION_CONTROLLER_AGENT_SIDECAR_KUBELET_API_LOGGING_ENABLED` Cluster Agent environment variable to `true`, so newly injected Agent containers will have kubelet logging enabled.

  ```yaml
  clusterAgent:
    admissionController:
      agentSidecarInjection:
        enabled: true
        provider: fargate
    env:
      - name: DD_ADMISSION_CONTROLLER_AGENT_SIDECAR_KUBELET_API_LOGGING_ENABLED
        value: true
  ```

  <!-- xxz tab xxx -->
  <!-- xxx tab "Manual" xxx -->

  To enable Agent logging manually, you must:
  1. Attach an [emptyDir][29] volume to your pod and mount it inside the Agent container. This prevents duplicate logs should the Agent container restart.
  2. Set `DD_LOGS_ENABLED` to `"true"` - this instructs the Agent to collect logs.
  3. Set `DD_LOGS_CONFIG_RUN_PATH` to the emptyDir mount path.
  4. Set `DD_LOGS_CONFIG_K8S_CONTAINER_USE_KUBELET_API` to `"true"` - this instructs the Agent on which logging method to use. 

  ```yaml
  apiVersion: apps/v1
  kind: Deployment
  spec:
    #(...)
    template:
      #(...)
      spec:
        # Empty dir to keep track of logging timestamps in case of agent restart
        volumes:
          - name: agent-option
            emptyDir: {}
        containers:
          # Your original container
          - name: "<CONTAINER_NAME>"
            image: "<CONTAINER_IMAGE>"

          # Running the Agent as a sidecar
          - name: datadog-agent
            image: gcr.io/datadoghq/agent:7
            # Mount the empty dir to the Agent
            volumeMounts:
              - name: agent-option
                mountPath: /opt/datadog-agent/run
                readOnly: false
            env:
              #(...)
              - name: DD_LOGS_ENABLED
                value: "true"
              - name: DD_LOGS_CONFIG_K8S_CONTAINER_USE_KUBELET_API
                value: "true"
              - name: DD_LOGS_CONFIG_RUN_PATH
                value: "/opt/datadog-agent/run"
            resources:
              requests:
                memory: "256Mi"
                cpu: "200m"
              limits:
                memory: "256Mi"
                cpu: "200m"
  ```

  <!-- xxz tab xxx -->
  <!-- xxz tabs xxx -->

2. You can configure the Agent sidecar to automatically collect logs for all of the containers in its pod by enabling `DD_LOGS_CONFIG_CONTAINER_COLLECT_ALL`. Alternatively, the log integration can be setup per container with the standard Kubernetes [Autodiscovery annotations][30].

  <!-- xxx tabs xxx -->
  <!-- xxx tab "Admission Controller - Datadog Operator" xxx -->

  ```yaml
  #(...)
  spec:
    #(...)
    features:
      admissionController:
        agentSidecarInjection:
          #(...)
          profiles:
            - env:
              # Collect all container logs
              - name: DD_LOGS_CONFIG_CONTAINER_COLLECT_ALL
                value: "true"
  ```

  <!-- xxz tab xxx -->
  <!-- xxx tab "Admission Controller - Helm" xxx -->

  ```yaml
  clusterAgent:
    admissionController:
      agentSidecarInjection:
        # (...)
        profiles:
          - env:
            # Collect all container logs
            - name: DD_LOGS_CONFIG_CONTAINER_COLLECT_ALL
              value: "true"
  ```

  <!-- xxz tab xxx -->
  <!-- xxx tab "Manual" xxx -->

  ```yaml
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: "<APPLICATION_NAME>"
      namespace: default
    spec:
      #(...)
      template:
      #(...)
        spec:
          #(...)
          containers:
            # Running the Agent as a sidecar
            - name: datadog-agent
              image: gcr.io/datadoghq/agent:7
              env:
                # Collect all container logs
                - name: DD_LOGS_CONFIG_CONTAINER_COLLECT_ALL
                  value: "true"
              #(...)
  ```

  <!-- xxz tab xxx -->
  <!-- xxz tabs xxx -->

### Collecting logs from EKS on Fargate with Fluent Bit

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
2. Use the [Datadog Forwarder][15] to collect logs from CloudWatch and send them to Datadog.

## Trace collection

In EKS Fargate, your application container sends its traces to the Datadog Agent sidecar container. The Agent accepts these traces over port `8126` by default.

You do not have to set the `DD_AGENT_HOST` address in your application container when sending these metrics. Let this default to `localhost`.

Set [`shareProcessNamespace: true` in the pod spec][13] to assist the Agent for origin detection.

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

      # Running the Agent as a sidecar
      - name: datadog-agent
        image: gcr.io/datadoghq/agent:7
        # (...)
```

[Read more about how to set up tracing][16].

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

Ensure you have the right permissions on the `ServiceAccount` associated with your pod. If your pod does not have a `ServiceAccount` associated with it or isn't bound to the correct ClusterRole, it does not have access to the Kubelet.

To validate your access, run:

```shell
kubectl auth can-i get nodes/pods --as system:serviceaccount:<NAMESPACE>:<SERVICEACCOUNT>
```

For example, if your Fargate pod is in the `fargate` namespace with the ServiceAccount `datadog-agent`:
```shell
kubectl auth can-i get nodes/pods --as system:serviceaccount:fargate:datadog-agent
```

This returns `yes` or `no` based on the access.


### Datadog Agent container security context

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
- [Trace API Gateway when proxying requests to ECS Fargate][28]

[1]: http://docs.datadoghq.com/integrations/system
[2]: https://docs.datadoghq.com/getting_started/agent/autodiscovery/
[3]: https://docs.aws.amazon.com/eks/latest/userguide/fargate-profile.html
[4]: http://docs.datadoghq.com/integrations/amazon_eks/#setup
[5]: http://docs.datadoghq.com/containers/kubernetes/installation
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
[26]: https://kubernetes.io/docs/concepts/configuration/secret/
[27]: https://helm.sh/docs/intro/install/
[28]: https://docs.datadoghq.com/tracing/trace_collection/proxy_setup/apigateway
[29]: https://kubernetes.io/docs/concepts/storage/volumes/#emptydir
[30]: https://docs.datadoghq.com/containers/kubernetes/log/?tab=helm#autodiscovery-annotations