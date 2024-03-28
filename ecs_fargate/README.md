# ECS Fargate Integration

## Overview

<div class="alert alert-warning"> This page describes the ECS Fargate integration. For EKS Fargate, see the documentation for Datadog's <a href="http://docs.datadoghq.com/integrations/eks_fargate">EKS Fargate integration</a>.
</div>

Get metrics from all your containers running in ECS Fargate:

- CPU/Memory usage & limit metrics
- Monitor your applications running on Fargate using Datadog integrations or custom metrics.

The Datadog Agent retrieves metrics for the task definition's containers with the ECS task metadata endpoint. According to the [ECS Documentation][2] on that endpoint:

- This endpoint returns Docker stats JSON for all of the containers associated with the task. For more information about each of the returned stats, see [ContainerStats][3] in the Docker API documentation.

The Task Metadata endpoint is only available from within the task definition itself, which is why the Datadog Agent needs to be run as an additional container within each task definition to be monitored.

The only configuration required to enable this metrics collection is to set an environment variable `ECS_FARGATE` to `"true"` in the task definition.

**Note**: Network Performance Monitoring (NPM) is not supported for ECS Fargate.

## Setup

The following steps cover setup of the Datadog Container Agent within AWS ECS Fargate. **Note**: Datadog Agent version 6.1.1 or higher is needed to take full advantage of the Fargate integration.

Tasks that do not have the Datadog Agent still report metrics with Cloudwatch, however the Agent is needed for Autodiscovery, detailed container metrics, tracing, and more. Additionally, Cloudwatch metrics are less granular, and have more latency in reporting than metrics shipped directly through the Datadog Agent.

### Installation

To monitor your ECS Fargate tasks with Datadog, run the Agent as a container in **same task definition** as your application container. To collect metrics with Datadog, each task definition should include a Datadog Agent container in addition to the application containers. Follow these setup steps:

1. **Create an ECS Fargate task**
2. **Create or Modify your IAM Policy**
3. **Run the task as a replica service**

#### Create an ECS Fargate task

The primary unit of work in Fargate is the task, which is configured in the task definition. A task definition is comparable to a pod in Kubernetes. A task definition must contain one or more containers. In order to run the Datadog Agent, create your task definition to run your application container(s), as well as the Datadog Agent container.

The instructions below show you how to configure the task using the [Amazon Web Console][4], [AWS CLI tools][5], or [AWS CloudFormation][6].

<!-- xxx tabs xxx -->
<!-- xxx tab "Web UI" xxx -->
##### Web UI Task Definition

<!-- partial
{{< site-region region="us,us3,us5,eu,ap1,gov" >}}

1. Log in to your [AWS Web Console][4] and navigate to the ECS section.
2. Click on **Task Definitions** in the left menu, then click the **Create new Task Definition** button or choose an existing Fargate task definition.
3. For new task definitions:
    1. Select **Fargate** as the launch type, then click the **Next step** button.
    2. Enter a **Task Definition Name**, such as `my-app-and-datadog`.
    3. Select a task execution IAM role. See permission requirements in the [Create or Modify your IAM Policy](#create-or-modify-your-iam-policy) section below.
    4. Choose **Task memory** and **Task CPU** based on your needs.
4. Click the **Add container** button to begin adding the Datadog Agent container.
    1. For **Container name** enter `datadog-agent`.
    2. For **Image** enter `public.ecr.aws/datadog/agent:latest`.
    3. For **Env Variables**, add the **Key** `DD_API_KEY` and enter your [Datadog API Key][41] as the value.
    4. Add another environment variable using the **Key** `ECS_FARGATE` and the value `true`. Click **Add** to add the container.
    5. Add another environment variable using the **Key** `DD_SITE` and the value {{< region-param key="dd_site" code="true" >}}. This defaults to `datadoghq.com` if you don't set it.
    6. (Windows Only) Select `C:\` as the working directory.
5. Add your other application containers to the task definition. For details on collecting integration metrics, see [Integration Setup for ECS Fargate][12].
6. Click **Create** to create the task definition.

[4]: https://aws.amazon.com/console
[12]: http://docs.datadoghq.com/integrations/faq/integration-setup-ecs-fargate
[41]: https://app.datadoghq.com/organization-settings/api-keys

{{< /site-region >}}
partial -->

<!-- xxz tab xxx -->

<!-- xxx tab "AWS CLI" xxx -->
##### AWS CLI Task Definition

1. Download [datadog-agent-ecs-fargate.json][42]. **Note**: If you are using Internet Explorer, this may download as a gzip file, which contains the JSON file mentioned below.
<!-- partial
{{< site-region region="us,us3,us5,eu,ap1,gov" >}}
2. Update the JSON with a `TASK_NAME`, your [Datadog API Key][41], and the appropriate `DD_SITE` ({{< region-param key="dd_site" code="true" >}}). **Note**: The environment variable `ECS_FARGATE` is already set to `"true"`.

[41]: https://app.datadoghq.com/organization-settings/api-keys
{{< /site-region >}}
partial -->
3. Add your other application containers to the task definition. For details on collecting integration metrics, see [Integration Setup for ECS Fargate][12].
4. Optionally - Add an Agent health check.

    Add the following to your ECS task definition to create an Agent health check:

    ```json
    "healthCheck": {
      "retries": 3,
      "command": ["CMD-SHELL","agent health"],
      "timeout": 5,
      "interval": 30,
      "startPeriod": 15
    }
    ```
5. Execute the following command to register the ECS task definition:

```bash
aws ecs register-task-definition --cli-input-json file://<PATH_TO_FILE>/datadog-agent-ecs-fargate.json
```

<!-- xxz tab xxx -->

<!-- xxx tab "CloudFormation" xxx -->
##### AWS CloudFormation Task Definition

You can use [AWS CloudFormation][6] templating to configure your Fargate containers. Use the `AWS::ECS::TaskDefinition` resource within your CloudFormation template to set the Amazon ECS task and specify `FARGATE` as the required launch type for that task.

<!-- partial
{{< site-region region="us,us3,us5,eu,ap1,gov" >}}
Update this CloudFormation template below with your [Datadog API Key][41]. As well as include the appropriate `DD_SITE` ({{< region-param key="dd_site" code="true" >}}) environment variable if necessary, as this defaults to `datadoghq.com` if you don't set it.

[41]: https://app.datadoghq.com/organization-settings/api-keys
{{< /site-region >}}
partial -->

```yaml
Resources:
  ECSTaskDefinition:
    Type: 'AWS::ECS::TaskDefinition'
    Properties:
      NetworkMode: awsvpc
      RequiresCompatibilities:
        - FARGATE
      Cpu: 256
      Memory: 512
      ContainerDefinitions:
        - Name: datadog-agent
          Image: 'public.ecr.aws/datadog/agent:latest'
          Environment:
            - Name: DD_API_KEY
              Value: <DATADOG_API_KEY>
            - Name: ECS_FARGATE
              Value: true
```

Lastly, include your other application containers within the `ContainerDefinitions` and deploy through CloudFormation.

For more information on CloudFormation templating and syntax, see the [AWS CloudFormation task definition documentation][43].


<!-- xxz tab xxx -->

<!-- xxz tabs xxx -->

For all of these examples, you can alternatively populate the `DD_API_KEY` environment variable by referencing the [ARN of a plaintext secret stored in AWS Secrets Manager][7]. Place the `DD_API_KEY` environment variable under the `containerDefinitions.secrets` section of the task definition file. Ensure that the task execution role has the necessary permission to fetch secrets from AWS Secrets Manager.

#### Create or modify your IAM policy

Add the following permissions to your [Datadog IAM policy][8] to collect ECS Fargate metrics. For more information, see the [ECS policies][9] on the AWS website.

| AWS Permission                   | Description                                                       |
| -------------------------------- | ----------------------------------------------------------------- |
| `ecs:ListClusters`               | List available clusters.                                          |
| `ecs:ListContainerInstances`     | List instances of a cluster.                                      |
| `ecs:DescribeContainerInstances` | Describe instances to add metrics on resources and tasks running. |

#### Run the task as a replica service

The only option in ECS Fargate is to run the task as a [Replica Service][10]. The Datadog Agent runs in the same task definition as your application and integration containers.

<!-- xxx tabs xxx -->
<!-- xxx tab "Web UI" xxx -->

##### Web UI Replica Service

1. Log in to your [AWS Web Console][4] and navigate to the ECS section. If needed, create a cluster with the **Networking only** cluster template.
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

<!-- xxz tab xxx -->

<!-- xxx tab "AWS CLI" xxx -->
##### AWS CLI Replica Service

Run the following commands using the [AWS CLI tools][5].

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
--region <AWS_REGION> --launch-type FARGATE --platform-version 1.4.0
```

<!-- xxz tab xxx -->

<!-- xxx tab "CloudFormation" xxx -->
##### AWS CloudFormation Replica Service

In the CloudFormation template you can reference the `ECSTaskDefinition` resource created in the previous example into the `AWS::ECS::Service` resource being created. After this specify your `Cluster`, `DesiredCount`, and any other parameters necessary for your application in your replica service.

```yaml
Resources:
  ECSTaskDefinition:
    #(...)
  ECSService:
    Type: 'AWS::ECS::Service'
    Properties:
      Cluster: <CLUSTER_NAME>
      TaskDefinition:
        Ref: "ECSTaskDefinition"
      DesiredCount: 1
      #(...)
```

For more information on CloudFormation templating and syntax, see the [AWS CloudFormation ECS service documentation][44].

<!-- xxz tab xxx -->

<!-- xxz tabs xxx -->
### Metric collection

After the Datadog Agent is setup as described above, the [ecs_fargate check][11] collects metrics with autodiscovery enabled. Add Docker labels to your other containers in the same task to collect additional metrics.

Although the integration works on Linux and Windows, some metrics are OS dependent. All metrics exposed when running on Windows are also exposed on Linux, but there are some metrics that are only available on Linux. See [Data Collected](#data-collected) for the list of metrics provided by this integration. The list also specifies which metrics are Linux-only.

For details on collecting integration metrics, see [Integration Setup for ECS Fargate][12].

#### DogStatsD

Metrics are collected with [DogStatsD][13] through UDP port 8125.

#### Other environment variables

For environment variables available with the Docker Agent container, see the [Docker Agent][14] page. **Note**: Some variables are not be available for Fargate.


| Environment Variable               | Description                                    |
|------------------------------------|------------------------------------------------|
| `DD_DOCKER_LABELS_AS_TAGS`         | Extract docker container labels                |
| `DD_CHECKS_TAG_CARDINALITY`        | Add tags to check metrics                      |
| `DD_DOGSTATSD_TAG_CARDINALITY`     | Add tags to custom metrics                     |

For global tagging, it is recommended to use `DD_DOCKER_LABELS_AS_TAGS`. With this method, the Agent pulls in tags from your container labels. This requires you to add the appropriate labels to your other containers. Labels can be added directly in the [task definition][15].

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

CloudFormation example (YAML):

```yaml
      ContainerDefinitions:
        - #(...)
          Environment:
            - Name: DD_DOCKER_LABELS_AS_TAGS
              Value: "{\"com.docker.compose.service\":\"service_name\"}"
```

**Note**: You should not use `DD_HOSTNAME` since there is no concept of a host to the user in Fargate. `DD_TAGS` is traditionally used to assign host tags, but as of Datadog Agent version 6.13.0 you can also use the environment variable to set global tags on your integration metrics.

### Crawler-based metrics

In addition to the metrics collected by the Datadog Agent, Datadog has a CloudWatch based ECS integration. This integration collects the [Amazon ECS CloudWatch Metrics][16].

As noted there, Fargate tasks also report metrics in this way:

> The metrics made available will depend on the launch type of the tasks and services in your clusters. If you are using the Fargate launch type for your services then CPU and memory utilization metrics are provided to assist in the monitoring of your services.

Since this method does not use the Datadog Agent, you need to configure the AWS integration by checking **ECS** on the integration tile. Then, Datadog pulls these CloudWatch metrics (namespaced `aws.ecs.*` in Datadog) on your behalf. See the [Data Collected][17] section of the documentation.

If these are the only metrics you need, you could rely on this integration for collection using CloudWatch metrics. **Note**: CloudWatch data is less granular (1-5 min depending on the type of monitoring you have enabled) and delayed in reporting to Datadog. This is because the data collection from CloudWatch must adhere to AWS API limits, instead of pushing it to Datadog with the Agent.

Datadog's default CloudWatch crawler polls metrics once every 10 minutes. If you need a faster crawl schedule, contact [Datadog support][18] for availability. **Note**: There are cost increases involved on the AWS side as CloudWatch bills for API calls.

### Log collection

You can monitor Fargate logs by using either:
- The AWS FireLens integration built on Datadog's Fluent Bit output plugin to send logs directly to Datadog
- Using the `awslogs` log driver to store the logs in a CloudWatch Log Group, and then a Lambda function to route logs to Datadog

Datadog recommends using AWS FireLens because you can configure Fluent Bit directly in your Fargate tasks.

#### Fluent Bit and FireLens

Configure the AWS FireLens integration built on Datadog's Fluent Bit output plugin to connect your FireLens monitored log data to Datadog Logs. You can find a full [sample task definition for this configuration here][19].

1. Add the Fluent Bit FireLens log router container in your existing Fargate task. For more information about enabling FireLens, see the dedicated [AWS Firelens docs][20]. For more information about Fargate container definitions, see the [AWS docs on Container Definitions][21]. AWS recommends that you use [the regional Docker image][22]. Here is an example snippet of a task definition where the Fluent Bit image is configured:

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

    If your containers are publishing serialized JSON logs over stdout, you should use this [extra FireLens configuration][23] to get them correctly parsed within Datadog:

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

    This converts serialized JSON from the `log:` field into top-level fields. See the AWS sample [Parsing container stdout logs that are serialized JSON][23] for more details.

2. Next, in the same Fargate task define a log configuration for the desired containers to ship logs. This log configuration should have AWS FireLens as the log driver, and with data being output to Fluent Bit. Here is an example snippet of a task definition where the FireLens is the log driver, and it is outputting data to Fluent Bit:

<!-- partial
{{< site-region region="us" >}}
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
{{< /site-region >}}
partial -->
<!-- partial
{{< site-region region="us3" >}}
  ```json
  {
    "logConfiguration": {
      "logDriver": "awsfirelens",
      "options": {
        "Name": "datadog",
        "apikey": "<DATADOG_API_KEY>",
        "Host": "http-intake.logs.us3.datadoghq.com",
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
{{< /site-region >}}
partial -->
<!-- partial
{{< site-region region="us5" >}}
  ```json
  {
    "logConfiguration": {
      "logDriver": "awsfirelens",
      "options": {
        "Name": "datadog",
        "apikey": "<DATADOG_API_KEY>",
        "Host": "http-intake.logs.us5.datadoghq.com",
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
{{< /site-region >}}
partial -->
<!-- partial
{{< site-region region="eu" >}}
  ```json
  {
    "logConfiguration": {
      "logDriver": "awsfirelens",
      "options": {
        "Name": "datadog",
        "apikey": "<DATADOG_API_KEY>",
        "Host": "http-intake.logs.datadoghq.eu",
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
{{< /site-region >}}
partial -->
<!-- partial
{{< site-region region="gov" >}}
  ```json
  {
    "logConfiguration": {
      "logDriver": "awsfirelens",
      "options": {
        "Name": "datadog",
        "apikey": "<DATADOG_API_KEY>",
        "Host": "http-intake.logs.ddog-gov.datadoghq.com",
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
{{< /site-region >}}
partial -->

<!-- partial
{{< site-region region="us,us3,us5,eu,ap1,gov" >}}
**Note**: Set your `apikey` as well as the `Host` relative to your respective site `http-intake.logs.`{{< region-param key="dd_site" code="true" >}}. The full list of available parameters is described in the [Datadog Fluent Bit documentation][24].

[24]: https://docs.datadoghq.com/integrations/fluentbit/#configuration-parameters
{{< /site-region >}}
partial -->

  The `dd_service`, `dd_source`, and `dd_tags` can be adjusted for your desired tags.

3. Whenever a Fargate task runs, Fluent Bit sends the container logs to Datadog with information about all of the containers managed by your Fargate tasks. You can see the raw logs on the [Log Explorer page][25], [build monitors][26] for the logs, and use the [Live Container view][27].

<!-- xxx tabs xxx -->
<!-- xxx tab "Web UI" xxx -->
##### Web UI

To add the Fluent Bit container to your existing Task Definition check the **Enable FireLens integration** checkbox under **Log router integration** to automatically create the `log_router` container for you. This pulls the regional image, however, we do recommend to use the `stable` image tag instead of `latest`. Once you click **Apply** this creates the base container. To further customize the `firelensConfiguration` click the **Configure via JSON** button at the bottom to edit this manually.

After this has been added edit the application container in your Task Definition that you want to submit logs from and change the **Log driver** to `awsfirelens` filling in the **Log options** with the keys shown in the above example.

<!-- xxz tab xxx -->

<!-- xxx tab "AWS CLI" xxx -->
##### AWS CLI

Edit your existing JSON task definition file to include the `log_router` container and the updated `logConfiguration` for your application container, as described in the previous section. After this is done, create a new revision of your task definition with the following command:

```bash
aws ecs register-task-definition --cli-input-json file://<PATH_TO_FILE>/datadog-agent-ecs-fargate.json
```

<!-- xxz tab xxx -->

<!-- xxx tab "CloudFormation" xxx -->
##### AWS CloudFormation

To use [AWS CloudFormation][6] templating, use the `AWS::ECS::TaskDefinition` resource and set the `Datadog` option to configure log management.

For example, to configure Fluent Bit to send logs to Datadog:

<!-- partial
{{< site-region region="us" >}}
```yaml
Resources:
  ECSTaskDefinition:
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
              apikey: <DATADOG_API_KEY>
              Host: http-intake.logs.datadoghq.com
              dd_service: test-service
              dd_source: test-source
              TLS: 'on'
              provider: ecs
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
{{< /site-region >}}
partial -->
<!-- partial
{{< site-region region="us3" >}}
```yaml
Resources:
  ECSTaskDefinition:
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
              apikey: <DATADOG_API_KEY>
              Host: http-intake.logs.us3.datadoghq.com
              dd_service: test-service
              dd_source: test-source
              TLS: 'on'
              provider: ecs
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
{{< /site-region >}}
partial -->
<!-- partial
{{< site-region region="us5" >}}
```yaml
Resources:
  ECSTaskDefinition:
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
              apikey: <DATADOG_API_KEY>
              Host: http-intake.logs.us5.datadoghq.com
              dd_service: test-service
              dd_source: test-source
              TLS: 'on'
              provider: ecs
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
{{< /site-region >}}
partial -->
<!-- partial
{{< site-region region="eu" >}}
```yaml
Resources:
  ECSTaskDefinition:
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
              apikey: <DATADOG_API_KEY>
              Host: http-intake.logs.datadoghq.eu
              dd_service: test-service
              dd_source: test-source
              TLS: 'on'
              provider: ecs
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
{{< /site-region >}}
partial -->
<!-- partial
{{< site-region region="gov" >}}
```yaml
Resources:
  ECSTaskDefinition:
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
              apikey: <DATADOG_API_KEY>
              Host: http-intake.logs.ddog-gov.datadoghq.com
              dd_service: test-service
              dd_source: test-source
              TLS: 'on'
              provider: ecs
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
{{< /site-region >}}
partial -->

For more information on CloudFormation templating and syntax, see the [AWS CloudFormation documentation][43].


<!-- xxz tab xxx -->

<!-- xxz tabs xxx -->

**Note**: Use a [TaskDefinition secret][28] to avoid exposing the `apikey` in plain text.

#### AWS log driver

Monitor Fargate logs by using the `awslogs` log driver and a Lambda function to route logs to Datadog.

1. Define the log driver as `awslogs` in the application container in your task you want to collect logs from. [Consult the AWS Fargate developer guide][29] for instructions.

2. This configures your Fargate tasks to send log information to Amazon CloudWatch Logs. The following shows a snippet of a task definition where the awslogs log driver is configured:

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

    For more information about using the `awslogs` log driver in your task definitions to send container logs to CloudWatch Logs, see [Using the awslogs Log Driver][30]. This driver collects logs generated by the container and sends them to CloudWatch directly.

3. Finally, use the [Datadog Lambda Log Forwarder function][31] to collect logs from CloudWatch and send them to Datadog.

### Trace collection

<!-- partial
{{< site-region region="us,us3,us5,eu,ap1,gov" >}}
1. Follow the [instructions above](#installation) to add the Datadog Agent container to your task definition with the additional environment variable `DD_APM_ENABLED` set to `true`. Set the `DD_SITE` variable to {{< region-param key="dd_site" code="true" >}}. It defaults to `datadoghq.com` if you don't set it.
{{< /site-region >}}
partial -->

2. Instrument your application based on your setup:

   **Note**: With Fargate APM applications, do **not** set `DD_AGENT_HOST` - the default of `localhost` works.

   | Language                           |
   |------------------------------------|
   | [Java][47] |
   | [Python][48] |
   | [Ruby][49] |
   | [Go][50] |
   | [Node.js][51] |
   | [PHP][52] |
   | [C++][53] |
   | [.NET Core][54] |
   | [.NET Framework][55] |

   See more general information about [Sending Traces to Datadog][32].

3. Ensure your application is running in the same task definition as the Datadog Agent container.

### Process collection

<div class="alert alert-warning">You can view your ECS Fargate processes in Datadog. To see their relationship to ECS Fargate containers, use the Datadog Agent v7.50.0 or later.</div>

You can monitor processes in ECS Fargate in Datadog by using the [Live Processes page][56]. To enable process collection, add the [`PidMode` parameter][57] in the Task Definition and set it to `task` as follows:

```text
"pidMode": "task"
```
To filter processes by ECS, use the `AWS Fargate` Containers facet or enter `fargate:ecs` in the search query on the Live Processes page.

## Out-of-the-box tags

The Agent can autodiscover and attach tags to all data emitted by the entire task or an individual container within this task. The list of tags automatically attached depends on the Agent's [cardinality configuration][33].

  | Tag                           | Cardinality  | Source               |
  |-------------------------------|--------------|----------------------|
  | `container_name`              | High         | ECS API              |
  | `container_id`                | High         | ECS API              |
  | `docker_image`                | Low          | ECS API              |
  | `image_name`                  | Low          | ECS API              |
  | `short_image`                 | Low          | ECS API              |
  | `image_tag`                   | Low          | ECS API              |
  | `ecs_cluster_name`            | Low          | ECS API              |
  | `ecs_container_name`          | Low          | ECS API              |
  | `task_arn`                    | Orchestrator | ECS API              |
  | `task_family`                 | Low          | ECS API              |
  | `task_name`                   | Low          | ECS API              |
  | `task_version`                | Low          | ECS API              |
  | `availability-zone`           | Low          | ECS API              |
  | `region`                      | Low          | ECS API              |

## Data Collected

### Metrics

See [metadata.csv][46] for a list of metrics provided by this integration. 

### Events

The ECS Fargate check does not include any events.

### Service Checks

See [service_checks.json][45] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][18].

## Further Reading

- Blog post: [Monitor AWS Fargate applications with Datadog][34]
- FAQ: [Integration Setup for ECS Fargate][12]
- Blog post: [Monitor your Fargate container logs with FireLens and Datadog][35]
- Blog post: [Key metrics for monitoring AWS Fargate][36]
- Blog post: [How to collect metrics and logs from AWS Fargate workloads][37]
- Blog post: [AWS Fargate monitoring with Datadog][38]
- Blog post: [Graviton2-powered AWS Fargate deployments][39]
- Blog post: [Monitor AWS Fargate for Windows containerized apps][40]
- Blog post: [Monitor processes running on AWS Fargate with Datadog][58]



[1]: http://docs.datadoghq.com/integrations/eks_fargate
[2]: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-metadata-endpoint.html
[3]: https://docs.docker.com/engine/api/v1.30/#operation/ContainerStats
[4]: https://aws.amazon.com/console
[5]: https://aws.amazon.com/cli
[6]: https://aws.amazon.com/cloudformation/
[7]: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/specifying-sensitive-data-tutorial.html
[8]: https://docs.datadoghq.com/integrations/amazon_web_services/#installation
[9]: https://docs.aws.amazon.com/IAM/latest/UserGuide/list_ecs.html
[10]: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_services.html#service_scheduler_replica
[11]: https://github.com/DataDog/integrations-core/blob/master/ecs_fargate/datadog_checks/ecs_fargate/data/conf.yaml.example
[12]: http://docs.datadoghq.com/integrations/faq/integration-setup-ecs-fargate
[13]: https://docs.datadoghq.com/developers/dogstatsd/
[14]: https://docs.datadoghq.com/agent/docker/#environment-variables
[15]: https://docs.aws.amazon.com/AmazonECS/latest/userguide/task_definition_parameters.html#container_definition_labels
[16]: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/cloudwatch-metrics.html
[17]: https://docs.datadoghq.com/integrations/amazon_ecs/#data-collected
[18]: https://docs.datadoghq.com/help/
[19]: https://github.com/aws-samples/amazon-ecs-firelens-examples/tree/mainline/examples/fluent-bit/datadog
[20]: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/using_firelens.html
[21]: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#container_definitions
[22]: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/using_firelens.html#firelens-using-fluentbit
[23]: https://github.com/aws-samples/amazon-ecs-firelens-examples/tree/master/examples/fluent-bit/parse-json
[24]: https://docs.datadoghq.com/integrations/fluentbit/#configuration-parameters
[25]: https://app.datadoghq.com/logs
[26]: https://docs.datadoghq.com/monitors/monitor_types/
[27]: https://docs.datadoghq.com/infrastructure/livecontainers/?tab=linuxwindows
[28]: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-ecs-taskdefinition-secret.html
[29]: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html
[30]: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/using_awslogs.html
[31]: https://docs.datadoghq.com/logs/guide/forwarder/
[32]: https://docs.datadoghq.com/tracing/setup/
[33]: https://docs.datadoghq.com/getting_started/tagging/assigning_tags/?tab=containerizedenvironments#environment-variables
[34]: https://www.datadoghq.com/blog/monitor-aws-fargate
[35]: https://www.datadoghq.com/blog/collect-fargate-logs-with-firelens/
[36]: https://www.datadoghq.com/blog/aws-fargate-metrics/
[37]: https://www.datadoghq.com/blog/tools-for-collecting-aws-fargate-metrics/
[38]: https://www.datadoghq.com/blog/aws-fargate-monitoring-with-datadog/
[39]: https://www.datadoghq.com/blog/aws-fargate-on-graviton2-monitoring/
[40]: https://www.datadoghq.com/blog/aws-fargate-windows-containers-support/
[41]: https://app.datadoghq.com/organization-settings/api-keys
[42]: https://docs.datadoghq.com/resources/json/datadog-agent-ecs-fargate.json
[43]: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ecs-taskdefinition.html
[44]: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ecs-service.html
[45]: https://github.com/DataDog/integrations-core/blob/master/ecs_fargate/assets/service_checks.json
[46]: https://github.com/DataDog/integrations-core/blob/master/ecs_fargate/metadata.csv
[47]: https://docs.datadoghq.com/tracing/trace_collection/dd_libraries/java?tab=containers#automatic-instrumentation
[48]: https://docs.datadoghq.com/tracing/trace_collection/dd_libraries/python?tab=containers#instrument-your-application
[49]: https://docs.datadoghq.com/tracing/trace_collection/dd_libraries/ruby#instrument-your-application
[50]: https://docs.datadoghq.com/tracing/trace_collection/dd_libraries/go/?tab=containers#activate-go-integrations-to-create-spans
[51]: https://docs.datadoghq.com/tracing/trace_collection/dd_libraries/nodejs?tab=containers#instrument-your-application
[52]: https://docs.datadoghq.com/tracing/trace_collection/dd_libraries/php?tab=containers#automatic-instrumentation
[53]: https://docs.datadoghq.com/tracing/trace_collection/dd_libraries/cpp?tab=containers#instrument-your-application
[54]: https://docs.datadoghq.com/tracing/trace_collection/dd_libraries/dotnet-core?tab=containers#custom-instrumentation
[55]: https://docs.datadoghq.com/tracing/trace_collection/dd_libraries/dotnet-framework?tab=containers#custom-instrumentation
[56]: https://app.datadoghq.com/process
[57]: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#other_task_definition_params
[58]: https://www.datadoghq.com/blog/monitor-fargate-processes/
