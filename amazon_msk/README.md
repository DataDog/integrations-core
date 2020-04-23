# Agent Check: Amazon MSK

## Overview

This check monitors Amazon Managed Streaming for Apache Kafka ([Amazon MSK][1]) through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

1. [Create a client machine][3] if one does not already exist
2. Ensure the client machine has been [granted][4] the permission policy [arn:aws:iam::aws:policy/AmazonMSKReadOnlyAccess][5] or equivalent [credentials][6] are available
3. Install the [Datadog Agent][7]

### Configuration

1. Edit the `amazon_msk.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Amazon MSK performance data. See the [sample amazon_msk.d/conf.yaml][8] for all available configuration options.

2. [Restart the Agent][9].

### Validation

[Run the Agent's status subcommand][10] and look for `amazon_msk` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][11] for a list of metrics provided by this check.

### Service Checks

**aws.msk.can_connect**:<br>
Returns `CRITICAL` if the Agent is unable to discover nodes of the MSK cluster. Otherwise, returns `OK`.

**aws.msk.prometheus.health**:<br>
Returns `CRITICAL` if the check cannot access a metrics endpoint. Otherwise, returns `OK`.

### Events

The Amazon MSK check does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][12].

[1]: https://aws.amazon.com/msk
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations
[3]: https://docs.aws.amazon.com/msk/latest/developerguide/create-client-machine.html
[4]: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html#attach-iam-role
[5]: https://console.aws.amazon.com/iam/home?#/policies/arn:aws:iam::aws:policy/AmazonMSKReadOnlyAccess
[6]: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#configuring-credentials
[7]: https://docs.datadoghq.com/agent
[8]: https://github.com/DataDog/integrations-core/blob/master/amazon_msk/datadog_checks/amazon_msk/data/conf.yaml.example
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[10]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[11]: https://github.com/DataDog/integrations-core/blob/master/amazon_msk/metadata.csv
[12]: https://docs.datadoghq.com/help
