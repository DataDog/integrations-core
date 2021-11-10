# Agent Check: Amazon MSK

## Overview

This check monitors Amazon Managed Streaming for Apache Kafka ([Amazon MSK][1]) through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

1. [Create a client machine][3] if one does not already exist
2. Ensure the client machine has been [granted][4] the permission policy [arn:aws:iam::aws:policy/AmazonMSKReadOnlyAccess][5] or equivalent [credentials][6] are available
3. Enable [open monitoring with Prometheus][7] on the MSK side to enable the JmxExporter and the NodeExporter.
4. Install the [Datadog Agent][8] on the client machine just created

### Configuration


1. Edit the `amazon_msk.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Amazon MSK performance data. See the [sample amazon_msk.d/conf.yaml][9] for all available configuration options.

   **Note**: This is the default OpenMetrics check example. If you previously implemented this integration, see the [legacy example][10].

2. [Restart the Agent][11].

### Validation

[Run the Agent's status subcommand][12] and look for `amazon_msk` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][13] for a list of metrics provided by this check.

### Events

The Amazon MSK check does not include any events.

### Service Checks

See [service_checks.json][14] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][15].

[1]: https://aws.amazon.com/msk
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: https://docs.aws.amazon.com/msk/latest/developerguide/create-client-machine.html
[4]: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html#attach-iam-role
[5]: https://console.aws.amazon.com/iam/home?#/policies/arn:aws:iam::aws:policy/AmazonMSKReadOnlyAccess
[6]: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#configuring-credentials
[7]: https://docs.aws.amazon.com/msk/latest/developerguide/open-monitoring.html
[8]: https://docs.datadoghq.com/agent/
[9]: https://github.com/DataDog/integrations-core/blob/master/amazon_msk/datadog_checks/amazon_msk/data/conf.yaml.example
[10]: https://github.com/DataDog/integrations-core/blob/7.31.x/amazon_msk/datadog_checks/amazon_msk/data/conf.yaml.example
[11]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[12]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[13]: https://github.com/DataDog/integrations-core/blob/master/amazon_msk/metadata.csv
[14]: https://github.com/DataDog/integrations-core/blob/master/amazon_msk/assets/service_checks.json
[15]: https://docs.datadoghq.com/help/
