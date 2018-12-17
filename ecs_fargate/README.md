# ECS Fargate Integration

## Overview

Get metrics from all your containers running in ECS Fargate:

* CPU/Memory usage & limit metrics
* Monitor your applications running on Fargate via Datadog integrations or custom metrics.

## Setup
The following steps cover setup of the Datadog Container Agent within AWS ECS Fargate. **Note**: Datadog Agent version 6.1.1 or higher is needed to take full advantage of the Fargate integration.

### Installation
To monitor your ECS Fargate tasks with Datadog, run the Agent as a container in same task definition as your application. To collect metrics with Datadog, each task definition should include a sidecar Datadog Agent container. Follow these setup steps:

1. **Add an ECS Fargate Task**
2. **Create or Modify your IAM Policy**
3. **Run the Task as a Replica Service**

#### Create an ECS Fargate Task
This task launches the Datadog Agent container. Configure the task using the [AWS CLI tools][11] or the [Amazon Web Console][12]. **Note**: To monitor your application or integrations, add them to this task.

##### AWS CLI

1. Download [datadog-agent-ecs-fargate.json][18].
2. Update the json with a **TASK_NAME** and your [Datadog API Key][13].
3. Add your other containers such as your app. For details on collecting integration metrics, see [Integration Setup for ECS Fargate][19].
3. Execute the following command to register the ECS task definition:
```
aws ecs register-task-definition --cli-input-json file://<PATH_TO_FILE>/datadog-agent-ecs-fargate.json
```

##### Web UI

1. Log in to your [AWS Web Console][12] and navigate to the ECS section.
2. Click on **Task Definitions** in the left menu, then click the **Create new Task Definition** button.
3. Select **Fargate** as the launch type, then click the **Next step** button.
4. Enter a **Task Definition Name**, such as `my-app-and-datadog`.
5. Select a Task execution IAM role. See permission requirements in the [Create or Modify your IAM Policy](##create-or-modify-your-iam-policy) section below.
6. Choose **Task memory** and **Task CPU** based on your needs.
7. Click the **Add container** button.
8. For **Container name** enter `datadog-agent`.
9. For **Image** enter `datadog/agent:latest`.
10. For **Memory Limits** enter `256` soft limit.
11. Scroll down to the **Advanced container configuration** section and enter `10` in **CPU units**.
12. For **Env Variables**, add the **Key** `DD_API_KEY` and enter your [Datadog API Key][13] as the value. *If you feel more comfortable storing secrets in s3, refer to the [ECS Configuration guide][14].*
13. Add another environment variable using the **Key** `ECS_FARGATE` and the value `true`. Click **Add** to add the container.
14. Add your other containers such as your app. For details on collecting integration metrics, see [Integration Setup for ECS Fargate][19].
15. Click **Create** to create the task definition.

#### Create or Modify your IAM Policy
Add the following permissions to your [Datadog IAM policy][15] to collect ECS Fargate metrics. For more information on ECS policies, [review the documentation on the AWS website][16].

| AWS Permission                   | Description                                                       |
|----------------------------------|-------------------------------------------------------------------|
| `ecs:ListClusters`               | List available clusters.                                          |
| `ecs:ListContainerInstances`     | List instances of a cluster.                                      |
| `ecs:DescribeContainerInstances` | Describe instances to add metrics on resources and tasks running. |

#### Run the Task as a Replica Service
The only option in ECS Fargate is to run the task as a [Replica Service][17]. The Datadog Agent runs as a sidecar in each Fargate task.

##### AWS CLI
Run the following commands using the [AWS CLI tools][11]. **Note**: Fargate version 1.1.0 or greater is required, so the command below specifies the platform version.

```
# If needed, create a cluster
aws ecs create-cluster --cluster-name "<CLUSTER_NAME>"

# Run the task as a service for your cluster
aws ecs run-task --cluster <CLUSTER_NAME> \
--network-configuration "awsvpcConfiguration={subnets=["<PRIVATE_SUBNET>"],securityGroups=["<SECURITY_GROUP>"]}" \
--task-definition arn:aws:ecs:us-east-1:<AWS_ACCOUNT_NUMBER>:task-definition/<TASK_NAME>:1 \
--region <AWS_REGION> --launch-type FARGATE --platform-version 1.1.0
```

##### Web UI
1. Log in to your [AWS Web Console][12] and navigate to the ECS section. If needed, create a cluster with the **Networking only** cluster template.
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

### Metric Collection
After the Datadog Agent is setup as described above, the [ecs_fargate check][6] collects metrics with autodiscovery enabled. Add Docker labels to your other containers in the same task to collect additional metrics.

For details on collecting integration metrics, see [Integration Setup for ECS Fargate][19].

#### DogStatsD
Metrics are collected with [DogStatsD][20] through UDP port 8125.

To send custom metrics by listening to DogStatsD packets from other containers, set the environment variable `DD_DOGSTATSD_NON_LOCAL_TRAFFIC` to `true` within the Datadog Agent container.

### Log Collection

1. Define the Fargate AwsLogDriver in your task. [Consult the AWS Fargate developer guide][8] for instructions.

2. Fargate task definitions only support the awslogs log driver for the log configuration. This configures your Fargate tasks to send log information to Amazon CloudWatch Logs. The following shows a snippet of a task definition where the awslogs log driver is configured:

    ```
    "logConfiguration": { 
       "logDriver": "awslogs",
       "options": { 
          "awslogs-group" : "/ecs/fargate-task-definition",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
    }
    ```

    For more information about using the awslogs log driver in your task definitions to send container logs to CloudWatch Logs, see [Using the awslogs Log Driver][9].

    This driver collects logs generated by the container and sends them to CloudWatch directly.

3. Finally, use a [Lambda function][10] to collect logs from CloudWatch and send them to Datadog.

## Data Collected

### Metrics

See [metadata.csv][2] for a list of metrics provided by this integration.

### Events

The ECS Fargate check does not include any events at this time.

### Service Checks

**fargate_check**  
Returns `CRITICAL` if the Agent is unable to connect to Fargate, otherwise returns `OK`.

## Troubleshooting

Need help? Contact [Datadog support][3].

## Further Reading

* Blog post: [Monitor AWS Fargate applications with Datadog][4]
* FAQ: [Integration Setup for ECS Fargate][19]


[1]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[2]: https://github.com/DataDog/integrations-core/blob/master/ecs_fargate/metadata.csv
[3]: https://docs.datadoghq.com/help/
[4]: https://www.datadoghq.com/blog/monitor-aws-fargate/
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[6]: https://github.com/DataDog/integrations-core/blob/master/ecs_fargate/datadog_checks/ecs_fargate/data/conf.yaml.example
[8]: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html
[9]: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/using_awslogs.html
[10]: https://docs.datadoghq.com/integrations/amazon_lambda/#log-collection
[11]: https://aws.amazon.com/cli/
[12]: https://aws.amazon.com/console/
[13]: https://app.datadoghq.com/account/settings#api
[14]: http://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-agent-config.html#ecs-config-s3
[15]: https://docs.datadoghq.com/integrations/amazon_web_services/#installation
[16]: https://docs.aws.amazon.com/IAM/latest/UserGuide/list_ecs.html
[17]: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_services.html#service_scheduler_replica
[18]: https://docs.datadoghq.com/json/datadog-agent-ecs-fargate.json
[19]: http://docs.datadoghq.com/integrations/faq/integration-setup-ecs-fargate/
[20]: https://docs.datadoghq.com/developers/dogstatsd/
