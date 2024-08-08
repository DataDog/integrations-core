# Agent Check: AWS Neuron

## Overview

This check monitors [AWS Neuron][1] through the Datadog Agent. It enables monitoring of the Inferentia and Trainium devices and delivers insights into your machine learning model's performance.

## Setup

Follow the instructions below to install and configure this check for an Agent running on an EC2 instance. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The AWS Neuron check is included in the [Datadog Agent][2] package.

You also need to install the [AWS Neuron Tools][11] package.

No additional installation is needed on your server.

### Configuration

1. Ensure that [Neuron Monitor][10] is being used to expose the Prometheus endpoint.

2. Edit the `aws_neuron.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your AWS Neuron performance data. See the [sample aws_neuron.d/conf.yaml][4] for all available configuration options.

3. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `aws_neuron` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The AWS Neuron integration does not include any events.

### Service Checks

The AWS Neuron integration does not include any service checks.

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

In containerized environments, ensure that the Agent has network access to the endpoints specified in the `aws_neuron.d/conf.yaml` file.
Need help? Contact [Datadog support][9].


[1]: https://awsdocs-neuron.readthedocs-hosted.com/en/latest/index.html
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/aws_neuron/datadog_checks/aws_neuron/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/aws_neuron/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/aws_neuron/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://awsdocs-neuron.readthedocs-hosted.com/en/latest/tools/neuron-sys-tools/neuron-monitor-user-guide.html#using-neuron-monitor-prometheus-py
[11]: https://awsdocs-neuron.readthedocs-hosted.com/en/latest/tools/index.html
