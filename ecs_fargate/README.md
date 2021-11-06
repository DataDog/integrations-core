# ECS Fargate Integration

## Overview

**Note**: This page describes the ECS Fargate integration. For EKS Fargate, see the documentation for Datadog's [EKS Fargate integration][1].

Get metrics from all your containers running in ECS Fargate:

- CPU/Memory usage & limit metrics
- Monitor your applications running on Fargate via Datadog integrations or custom metrics.

The Datadog Agent retrieves metrics for the task definition's containers with the ECS task metadata endpoint. According to the [ECS Documentation][2] on that endpoint:

> This endpoint returns Docker stats JSON for all of the containers associated with the task. For more information about each of the returned stats, see [ContainerStats][3] in the Docker API documentation.

The Task Metadata endpoint is only available from within the task definition itself, which is why the Datadog Agent needs to be run as an additional container within the task definition.

The only configuration required to enable this metrics collection is to set an environment variable `ECS_FARGATE` to `"true"` in the task definition.

## Setup

The following steps cover setup of the Datadog Container Agent within AWS ECS Fargate. **Note**: Datadog Agent version 6.1.1 or higher is needed to take full advantage of the Fargate integration.

Tasks that do not have the Datadog Agent still report metrics via Cloudwatch, however the Agent is needed for Autodiscovery, detailed container metrics, tracing, and more. Additionally, Cloudwatch metrics are less granular, and have more latency in reporting than metrics shipped directly via the Datadog Agent.

### Installation

To monitor your ECS Fargate tasks with Datadog, run the Agent as a container in same task definition as your application. To collect metrics with Datadog, each task definition should include a Datadog Agent container in addition to the application containers. Follow these setup steps:

1. **Create an ECS Fargate task**
2. **Create or Modify your IAM Policy**
3. **Run the task as a replica service**

#### Create an ECS Fargate task

The primary unit of work in Fargate is the task, which is configured in the task definition. A task definition is comparable to a pod in Kubernetes. A task definition must contain one or more containers. In order to run the Datadog Agent, create your task definition to run your application container(s), as well as the Datadog Agent container.

The instructions below show you how to configure the task using the [AWS CLI tools][4] or the [Amazon Web Console][5].

##### Web UI

1. Log in to your [AWS Web Console][5] and navigate to the ECS section.
2. Click on **Task Definitions** in the left menu, then click the **Create new Task Definition** button.
3. Select **Fargate** as the launch type, then click the **Next step** button.
4. Enter a **Task Definition Name**, such as `my-app-and-datadog`.
5. Select a task execution IAM role. See permission requirements in the [Create or Modify your IAM Policy](#create-or-modify-your-iam-policy) section below.
6. Choose **Task memory** and **Task CPU** based on your needs.
7. Click the **Add container** button.
8. For **Container name** enter `datadog-agent`.
9. For **Image** enter `datadog/agent:latest`.
10. For **Memory Limits** enter `256` soft limit.
11. Scroll down to the **Advanced container configuration** section and enter `10` in **CPU units**.
12. For **Env Variables**, add the **Key** `DD_API_KEY` and enter your [Datadog API Key][6] as the value. _If you feel more comfortable storing secrets in s3, refer to the [ECS Configuration guide][7]._
13. Add another environment variable using the **Key** `ECS_FARGATE` and the value `true`. Click **Add** to add the container.
14. Add another environment variable using the **Key** `DD_SITE` and the value {{< region-param key="dd_site" code="true" >}}. This defaults to `datadoghq.com` if you don't set it.
15. (Windows Only) Select "C:\" as the working directory.
16. Add your other containers such as your app. For details on collecting integration metrics, see [Integration Setup for ECS Fargate][8].
17. Click **Create** to create the task definition.

##### AWS CLI

1. Download [datadog-agent-ecs-fargate][9]. **Note**: If you are using IE, this may download as gzip file, which contains the JSON file mentioned below.**
2. Update the JSON with a `TASK_NAME`, your [Datadog API Key][6], and the appropriate `DD_SITE` ({{< region-param key="dd_site" code="true" >}}). Note that the environment variable `ECS_FARGATE` is already set to `"true"`.
3. Add your other containers such as your app. For details on collecting integration metrics, see [Integration Setup for ECS Fargate][8].
4. Execute the following command to register the ECS task definition:

```bash
aws ecs register-task-definition --cli-input-json file://<PATH_TO_FILE>/datadog-agent-ecs-fargate.json
```

##### AWS CloudFormation

You can use [AWS CloudFormation][10] templating to configure your Fargate containers. Use the `AWS::ECS::TaskDefinition` resource within your CloudFormation template to set the Amazon ECS task and specify `FARGATE` as the required launch type for that task. You can then set the `Datadog` option to configure log management, like in the example below:

```yaml
Resources:
  ECSTDNJH3:
    Type: 'AWS::ECS::TaskDefinition'
    Properties:
      NetworkMode: awsvpc
      RequiresCompatibilities:
          - FARGATE
      Cpu: 256
      Memory: 1GB
      ContainerDefinitions:
        - Name: tomcat-test
          Image: 'tomcat:jdk8-adoptopenjdk-openj9'
          LogConfiguration:
            LogDriver: awsfirelens
            Options:
              Name: datadog
              Host: http-intake.logs.datadoghq.com
              TLS: 'on'
              dd_service: test-service
              dd_source: test-source
              provider: ecs
              apikey: <API_KEY>
          MemoryReservation: 500
        - Name: log_router
          Image: 'amazon/aws-for-fluent-bit:stable'
          Essential: true
          FirelensConfiguration:
            Type: fluentbit
            Options:
              enable-ecs-log-metadata: true
          MemoryReservation: 50
```
**Note**: Use a [TaskDefinition secret][11] to avoid exposing the `apikey` in plain text.

For more information on CloudFormation templating and syntax, review the [AWS CloudFormation documentation][12].

#### Create or modify your IAM policy

Add the following permissions to your [Datadog IAM policy][13] to collect ECS Fargate metrics. For more information on ECS policies, [review the documentation on the AWS website][14].

| AWS Permission                   | Description                                                       |
| -------------------------------- | ----------------------------------------------------------------- |
| `ecs:ListClusters`               | List available clusters.                                          |
| `ecs:ListContainerInstances`     | List instances of a cluster.                                      |
| `ecs:DescribeContainerInstances` | Describe instances to add metrics on resources and tasks running. |

#### Run the task as a replica service

The only option in ECS Fargate is to run the task as a [Replica Service][15]. The Datadog Agent runs in the same task definition as your application and integration containers.

##### AWS CLI

Run the following commands using the [AWS CLI tools][4].

**Note**: Fargate version 1.1.0 or greater is required, so the command below specifies the platform version.

If needed, create a cluster:

```bash
aws ecs create-cluster --cluster-name "<CLUSTER_NAME>"
```

Run the task as a service for your cluster:

```bash
aws ecs run-task --cluster <CLUSTER_NAME> \
--network-configuration "awsvpcConfiguration={subnets=["<PRIVATE_SUBNET>"],securityGroups=["<SECURITY_GROUP>"]}" \
--task-definition arn:aws:ecs:us-east-1:<AWS_ACCOUNT_NUMBER>:task-definition/<TASK_NAME>:1 \
--region <AWS_REGION> --launch-type FARGATE --platform-version 1.1.0
```

##### Web UI

1. Log in to your [AWS Web Console][5] and navigate to the ECS section. If needed, create a cluster with the **Networking only** cluster template.
2. Choose the cluster to run the Datadog Agent on.
3. On the **Services** tab, click the **Create** button.
4. For **Launch type**, choose **FARGATE**.
5. For **Task Definition**, select the task created in the previous steps.
6. Enter a **Service name**.
7. For **Number of tasks** enter `1`, then click the **Next step** button.
8. Select the **Cluster VPC**, **Subnets**, and **Security Groups**.
9. **Load balancing** and **Service discovery** are optional based on your preference.
10. Click the **Next step** button.
11. **Auto Scaling** is optional based on your preference.
12. Click the **Next step** button, then click the **Create service** button.

### Metric collection

After the Datadog Agent is setup as described above, the [ecs_fargate check][16] collects metrics with autodiscovery enabled. Add Docker labels to your other containers in the same task to collect additional metrics.

For details on collecting integration metrics, see [Integration Setup for ECS Fargate][8].

#### DogStatsD

Metrics are collected with [DogStatsD][17] through UDP port 8125.

To send custom metrics by listening to DogStatsD packets from other containers, set the environment variable `DD_DOGSTATSD_NON_LOCAL_TRAFFIC` to `true` within the Datadog Agent container.

#### Other environment variables

For environment variables available with the Docker Agent container, see the [Docker Agent][18] page. **Note**: Some variables are not be available for Fargate.


| Environment Variable               | Description                                    |
|------------------------------------|------------------------------------------------|
| `DD_DOCKER_LABELS_AS_TAGS`         | Extract docker container labels                |
| `DD_DOCKER_ENV_AS_TAGS`            | Extract docker container environment variables |
| `DD_KUBERNETES_POD_LABELS_AS_TAGS` | Extract pod labels                             |
| `DD_CHECKS_TAG_CARDINALITY`        | Add tags to check metrics                      |
| `DD_DOGSTATSD_TAG_CARDINALITY`     | Add tags to custom metrics                     |

For global tagging, it is recommended to use `DD_DOCKER_LABELS_AS_TAGS`. With this method, the Agent pulls in tags from your Docker container labels. This requires you to add the appropriate labels to your other Docker containers. Labels can be added directly in the [task definition][19].

Format for the Agent container:

```json
{
  "name": "DD_DOCKER_LABELS_AS_TAGS",
  "value": "{\"<LABEL_NAME_TO_COLLECT>\":\"<TAG_KEY_FOR_DATADOG>\"}"
}
```

Example for the Agent container:

```json
{
  "name": "DD_DOCKER_LABELS_AS_TAGS",
  "value": "{\"com.docker.compose.service\":\"service_name\"}"
}
```

**Note**: You should not use `DD_HOSTNAME` since there is no concept of a host to the user in Fargate. `DD_TAGS` is traditionally used to assign host tags, but as of Datadog Agent version 6.13.0 you can also use the environment variable to set global tags on your integration metrics.

### Crawler-based metrics

In addition to the metrics collected by the Datadog Agent, Datadog has a CloudWatch based ECS integration. This integration collects the [Amazon ECS CloudWatch Metrics][20].

As noted there, Fargate tasks also report metrics in this way:

> The metrics made available will depend on the launch type of the tasks and services in your clusters. If you are using the Fargate launch type for your services then CPU and memory utilization metrics are provided to assist in the monitoring of your services.

Since this method does not use the Datadog Agent, you need to configure our AWS integration by checking **ECS** on the integration tile. Then, our application pulls these CloudWatch metrics (namespaced `aws.ecs.*` in Datadog) on your behalf. See the [Data Collected][21] section of the documentation.

If these are the only metrics you need, you could rely on this integration for collection via CloudWatch metrics. **Note**: CloudWatch data is less granular (1-5 min depending on the type of monitoring you have enabled) and delayed in reporting to Datadog. This is because the data collection from CloudWatch must adhere to AWS API limits, instead of pushing it to Datadog with the Agent.

Datadog's default CloudWatch crawler polls metrics once every 10 minutes. If you need a faster crawl schedule, contact [Datadog support][22] for availability. **Note**: There are cost increases involved on the AWS side as CloudWatch bills for API calls.

### Log collection

You can monitor Fargate logs by using the AWS FireLens integration built on Datadogs Fluentbit output plugin to send logs to Datadog, or by using the `awslogs` log driver and a Lambda function to route logs to Datadog. Datadog recommends using AWS FireLens because you can configure Fluent Bit directly in your Fargate tasks.

<!-- xxx tabs xxx -->
<!-- xxx tab "Fluent Bit and Firelens" xxx -->
#### Fluent Bit and FireLens

Configure the AWS FireLens integration built on Datadog's Fluent Bit output plugin to connect your FireLens monitored log data to Datadog Logs.

1. Enable Fluent Bit in the FireLens log router container in your Fargate task. For more information about enabling FireLens, see the dedicated [AWS Firelens docs][23]. For more information about Fargate container definitions, see the [AWS docs on Container Definitions][24]. AWS recommends that you use [the regional Docker image][25]. Here is an example snippet of a task definition where the Fluent Bit image is configured:

   ```json
   {
     "essential": true,
     "image": "amazon/aws-for-fluent-bit:stable",
     "name": "log_router",
     "firelensConfiguration": {
       "type": "fluentbit",
       "options": { "enable-ecs-log-metadata": "true" }
     }
   }
   ```

    If your containers are publishing serialized JSON logs over stdout, you should use this [extra firelens configuration][26] to get them correctly parsed within Datadog:

   ```json
   {
     "essential": true,
     "image": "amazon/aws-for-fluent-bit:stable",
     "name": "log_router",
     "firelensConfiguration": {
       "type": "fluentbit",
       "options": {
         "enable-ecs-log-metadata": "true",
         "config-file-type": "file",
         "config-file-value": "/fluent-bit/configs/parse-json.conf"
       }
     }
   }
   ```

    This converts serialized JSON from the `log:` field into top-level fields. See the AWS sample [Parsing container stdout logs that are serialized JSON][26] for more details.

2. Next, in the same Fargate task, define a log configuration with AWS FireLens as the log driver, and with data being output to Fluent Bit. Here is an example snippet of a task definition where the FireLens is the log driver, and it is outputting data to Fluent Bit:

   ```json
   {
     "logConfiguration": {
       "logDriver": "awsfirelens",
       "options": {
         "Name": "datadog",
         "apikey": "<DATADOG_API_KEY>",
         "Host": "http-intake.logs.datadoghq.com",
         "dd_service": "firelens-test",
         "dd_source": "redis",
         "dd_message_key": "log",
         "dd_tags": "project:fluentbit",
         "TLS": "on",
         "provider": "ecs"
       }
     }
   }
   ```

    **Note**: If your organization is in Datadog EU site, use `http-intake.logs.datadoghq.eu` for the `Host` option instead. The full list of available parameters is described in the [Datadog Fluentbit documentation][27].

3. Now, whenever a Fargate task runs, Fluent Bit sends the container logs to your Datadog monitoring with information about all of the containers managed by your Fargate tasks. You can see the raw logs on the [Log Explorer page][28], [build monitors][29] for the logs, and use the [Live Container view][30].

 
<!-- xxz tab xxx -->
<!-- xxx tab "logDriver" xxx -->

#### AWS log driver

Monitor Fargate logs by using the `awslogs` log driver and a Lambda function to route logs to Datadog.

1. Define the Fargate AwsLogDriver in your task. [Consult the AWS Fargate developer guide][31] for instructions.

2. Fargate task definitions only support the awslogs log driver for the log configuration. This configures your Fargate tasks to send log information to Amazon CloudWatch Logs. The following shows a snippet of a task definition where the awslogs log driver is configured:

   ```json
   {
     "logConfiguration": {
       "logDriver": "awslogs",
       "options": {
         "awslogs-group": "/ecs/fargate-task-definition",
         "awslogs-region": "us-east-1",
         "awslogs-stream-prefix": "ecs"
       }
     }
   }
   ```

    For more information about using the awslogs log driver in your task definitions to send container logs to CloudWatch Logs, see [Using the awslogs Log Driver][32]. This driver collects logs generated by the container and sends them to CloudWatch directly.

3. Finally, use a [Lambda function][33] to collect logs from CloudWatch and send them to Datadog.


<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Trace collection

1. Follow the [instructions above](#installation) to add the Datadog Agent container to your task definition with the additional environment variable `DD_APM_ENABLED` set to `true` and set up a host port that uses **8126** with **tcp** protocol under port mappings. Set the `DD_SITE` variable to {{< region-param key="dd_site" code="true" >}}. It defaults to `datadoghq.com` if you don't set it.

2. [Instrument your application][34] based on your setup.

3. Ensure your application is running in the same task definition as the Datadog Agent container.

## Data Collected

### Metrics

This integration works on Linux and Windows, but some metrics are OS dependent. All the metrics exposed when running on Windows are also exposed on Linux, but there are some metrics that are only available on Linux.

See [metadata.csv][35] for a list of metrics provided by this integration. It also specifies which ones are Linux-only.

### Events

The ECS Fargate check does not include any events.

### Service Checks

See [service_checks.json][36] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][22].

## Further Reading

- Blog post: [Monitor AWS Fargate applications with Datadog][37]
- FAQ: [Integration Setup for ECS Fargate][8]
- Blog post: [Monitor your Fargate container logs with FireLens and Datadog][38]
- Blog post: [Key metrics for monitoring AWS Fargate][39]
- Blog post: [How to collect metrics and logs from AWS Fargate workloads][40]
- Blog post: [AWS Fargate monitoring with Datadog][41]

[1]: http://docs.datadoghq.com/integrations/eks_fargate
[2]: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-metadata-endpoint.html
[3]: https://docs.docker.com/engine/api/v1.30/#operation/ContainerStats
[4]: https://aws.amazon.com/cli
[5]: https://aws.amazon.com/console
[6]: https://app.datadoghq.com/organization-settings/api-keys
[7]: http://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-agent-config.html#ecs-config-s3
[8]: http://docs.datadoghq.com/integrations/faq/integration-setup-ecs-fargate
[9]: https://docs.datadoghq.com/resources/json/datadog-agent-ecs-fargate.json
[10]: https://aws.amazon.com/cloudformation/
[11]: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-ecs-taskdefinition-secret.html
[12]: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ecs-service.html
[13]: https://docs.datadoghq.com/integrations/amazon_web_services/#installation
[14]: https://docs.aws.amazon.com/IAM/latest/UserGuide/list_ecs.html
[15]: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_services.html#service_scheduler_replica
[16]: https://github.com/DataDog/integrations-core/blob/master/ecs_fargate/datadog_checks/ecs_fargate/data/conf.yaml.example
[17]: https://docs.datadoghq.com/developers/dogstatsd/
[18]: https://docs.datadoghq.com/agent/docker/#environment-variables
[19]: https://docs.aws.amazon.com/AmazonECS/latest/userguide/task_definition_parameters.html#container_definition_labels
[20]: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/cloudwatch-metrics.html
[21]: https://docs.datadoghq.com/integrations/amazon_ecs/#data-collected
[22]: https://docs.datadoghq.com/help/
[23]: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/using_firelens.html
[24]: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#container_definitions
[25]: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/using_firelens.html#firelens-using-fluentbit
[26]: https://github.com/aws-samples/amazon-ecs-firelens-examples/tree/master/examples/fluent-bit/parse-json
[27]: https://docs.datadoghq.com/integrations/fluentbit/#configuration-parameters
[28]: https://app.datadoghq.com/logs
[29]: https://docs.datadoghq.com/monitors/monitor_types/
[30]: https://docs.datadoghq.com/infrastructure/livecontainers/?tab=linuxwindows
[31]: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html
[32]: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/using_awslogs.html
[33]: https://docs.datadoghq.com/integrations/amazon_lambda/#log-collection
[34]: https://docs.datadoghq.com/tracing/setup/
[35]: https://github.com/DataDog/integrations-core/blob/master/ecs_fargate/metadata.csv
[36]: https://github.com/DataDog/integrations-core/blob/master/ecs_fargate/assets/service_checks.json
[37]: https://www.datadoghq.com/blog/monitor-aws-fargate
[38]: https://www.datadoghq.com/blog/collect-fargate-logs-with-firelens/
[39]: https://www.datadoghq.com/blog/aws-fargate-metrics/
[40]: https://www.datadoghq.com/blog/tools-for-collecting-aws-fargate-metrics/
[41]: https://www.datadoghq.com/blog/aws-fargate-monitoring-with-datadog/
