## Overview

[AWS App Mesh][1] is a service mesh that provides application-level networking to your micro services running on Amazon ECS Fargate or Amazon EKS clusters.


**Minimum Agent version:** 6.15.0

## Setup

<!-- xxx tabs xxx -->
<!-- xxx tab "EKS" xxx -->

Use the instructions below to enable metric collection for the AWS App Mesh proxy sidecar, called Envoy. Users can choose to add sidecars in one of three modes: deploying, patching the deployment later, or using the AWS App Mesh injector controller. All modes are supported by the following steps.

#### Metric collection

**Prerequisite**: Deploy Datadog Agents as a DaemonSet in your Kubernetes cluster using the [EKS integration][1] documentation.

1. Due to limitations in App Mesh, forwarding metrics from EKS to Datadog requires the Egress filter to be set to `Allow External Traffic`.

2. Create a ConfigMap in your cluster to automatically discover App Mesh's Envoy side cars that are added to each pod:

    ```yaml
      apiVersion: v1
      kind: ConfigMap
      metadata:
      name: datadog-config
      data:
      envoy: |-
        ad_identifiers:
        - aws-appmesh-envoy
        init_config:
        instances:
        - stats_url: http://%%host%%:9901/stats
          tags:
            - <TAG_KEY>:<TAG_VALUE>  # Example - cluster:eks-appmesh
    ```

3. Update the `volumeMounts` object in your Datadog Agent's DaemonSet YAML file:

    ```yaml
          volumeMounts:
           - name: datadog-config
             mountPath: /conf.d
    ```

4. Update the `volumes` object in your Datadog Agent's DaemonSet YAML file:

    ```yaml
         volumes:
          - name: datadog-config
            configMap:
              name: datadog-config
              items:
              - key: envoy
                path: envoy.yaml
    ```

#### Log collection

<!-- partial
{{< site-region region="us3" >}}

Log collection is not supported for this site.

{{< /site-region >}}
partial -->

<!-- partial
{{< site-region region="us,eu,gov" >}}

To enable log collection, update the Agent's DaemonSet with the dedicated [Kubernetes log collection instructions][1].

[1]: https://docs.datadoghq.com/integrations/ecs_fargate/#log-collection

{{< /site-region >}}
partial -->

#### Trace collection

Select the namespace to deploy the `datadog-agent` and service, for example: `monitoring`. Use this in the option to deploy the appmesh-injector with:

```shell
  helm upgrade -i appmesh-controller eks/appmesh-controller \
  --namespace appmesh-system \
  --set sidecar.logLevel=debug \
  --set tracing.enabled=true \
  --set tracing.provider=datadog \
  --set tracing.address=ref:status.hostIP \
  --set tracing.port=8126
```


Alternatively, the appmesh injector can be deployed by following the [App Mesh with EKS][3] documentation using the option `enable-datadog-tracing=true` or environment variable `ENABLE_DATADOG_TRACING=true`.

[1]: https://docs.datadoghq.com/integrations/amazon_eks/
[2]: /agent/kubernetes/daemonset_setup/#log-collection
[3]: https://github.com/aws/aws-app-mesh-examples/blob/master/walkthroughs/eks/base.md#install-app-mesh--kubernetes-components

<!-- xxz tab xxx -->
<!-- xxx tab "ECS Fargate" xxx -->

#### Metric collection

**Prerequisite**: Add Datadog Agents to each of your Fargate task definitions with App Mesh enabled, such as an Envoy sidecar injected, using the [ECS Fargate integration][1] documentation.

1. Due to limitations in App Mesh, forwarding metrics from an ECS task to Datadog requires the Egress filter to be set to `Allow External Traffic`.

2. Update all task definitions containing the Envoy sidecar and Datadog Agent with the following Docker labels. See [Integration Setup for ECS Fargate][2] for details.

    ```text
        "dockerLabels": {
              com.datadoghq.ad.instances : [{"stats_url": "http://%%host%%:9901/stats"}]
              com.datadoghq.ad.check_names : ["envoy"]
              com.datadoghq.ad.init_configs : [{}]
            },
    ```

#### Log collection

<!-- partial
{{< site-region region="us3" >}}

Log collection is not supported for this site.

{{< /site-region >}}
partial -->

<!-- partial
{{< site-region region="us,eu,gov" >}}

Enable log collection with the instructions in the [ECS Fargate integration documentation][1].

[1]: https://docs.datadoghq.com/integrations/ecs_fargate/#log-collection

{{< /site-region >}}
partial -->

#### Trace collection

1. Enable trace collection with the instructions in the [ECS Fargate integration][4] documentation.

Set the AWS App Mesh parameters `ENABLE_ENVOY_DATADOG_TRACING` and `DATADOG_TRACER_PORT` as environment variables in the ECS Fargate task definition. Learn more in the [AWS App Mesh][5] documentation.

[1]: https://docs.datadoghq.com/integrations/ecs_fargate/
[2]: https://docs.datadoghq.com/integrations/faq/integration-setup-ecs-fargate/
[3]: https://docs.datadoghq.com/integrations/ecs_fargate/#log-collection
[4]: https://docs.datadoghq.com/integrations/ecs_fargate/#trace-collection
[5]: https://docs.aws.amazon.com/app-mesh/latest/userguide/envoy.html

<!-- xxz tab xxx -->
<!-- xxx tab "ECS EC2" xxx -->

#### Metric collection

**Prerequisite**: Add Datadog Agents to each of your ECS EC2 task definitions with App Mesh enabled, such as an Envoy sidecar injected, using the [ECS integration][1] documentation.

1. Due to limitations in App Mesh, forwarding metrics from an ECS task to Datadog requires the Egress filter to be set to `Allow External Traffic`.

2. Update all task definitions containing the Envoy sidecar and Datadog Agent with the following Docker labels. See [Integration Setup for ECS Fargate][2] for details.

    ```text
        "dockerLabels": {
              com.datadoghq.ad.instances : [{"stats_url": "http://%%host%%:9901/stats"}]
              com.datadoghq.ad.check_names : ["envoy"]
              com.datadoghq.ad.init_configs : [{}]
            },
    ```

#### Log collection

<!-- partial
{{< site-region region="us3" >}}

Log collection is not supported for this site.

{{< /site-region >}}
partial -->

<!-- partial
{{< site-region region="us,eu,gov" >}}

Enable log collection with the instructions in the [ECS integration documentation][1].

[1]: https://docs.datadoghq.com/integrations/amazon_ecs/#log-collection

{{< /site-region >}}
partial -->

#### Trace collection

1. Enable trace collection with the instructions in the [ECS integration][4] documentation.

2. Set the AWS App Mesh parameters `ENABLE_ENVOY_DATADOG_TRACING` and `DATADOG_TRACER_PORT` as environment variables in the ECS task definition. Learn more in the [AWS App Mesh][5] documentation.

[1]: https://docs.datadoghq.com/integrations/amazon_ecs/
[2]: https://docs.datadoghq.com/integrations/faq/integration-setup-ecs-fargate/
[3]: https://docs.datadoghq.com/integrations/amazon_ecs/#log-collection
[4]: https://docs.datadoghq.com/integrations/amazon_ecs/#trace-collection
[5]: https://docs.aws.amazon.com/app-mesh/latest/userguide/envoy.html

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

## Data Collected

### Metrics

See the [Envoy integration][2] for a list of metrics.

### Events

The AWS App Mesh integration does not include any events.

### Service Checks

The AWS App Mesh integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][3].

## Further Reading

- [Envoy integration][4]

[1]: https://aws.amazon.com/app-mesh
[2]: https://docs.datadoghq.com/integrations/envoy/#metrics
[3]: https://docs.datadoghq.com/help/
[4]: https://docs.datadoghq.com/integrations/envoy/
