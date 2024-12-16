# Agent Check: AWS Inferentia and AWS Trainium Monitoring

## Overview

This check monitors [AWS Neuron][1] through the Datadog Agent. It enables monitoring of the Inferentia and Trainium devices and delivers insights into your machine learning model's performance.

## Setup

Follow the instructions below to install and configure this check for an Agent running on an EC2 instance. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The AWS Neuron check is included in the [Datadog Agent][2] package.

You also need to install the [AWS Neuron Tools][11] package.

No additional installation is needed on your server.

### Configuration

#### Metrics

1. Ensure that [Neuron Monitor][10] is being used to expose the Prometheus endpoint.

2. Edit the `aws_neuron.d/conf.yaml` file, which is located in the `conf.d/` folder at the root of your [Agent's configuration directory][12], to start collecting your AWS Neuron performance data. See the [sample aws_neuron.d/conf.yaml][4] for all available configuration options.

3. [Restart the Agent][5].

#### Logs

The AWS Neuron integration can collect logs from the Neuron containers and forward them to Datadog.

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Uncomment and edit the logs configuration block in your `aws_neuron.d/conf.yaml` file. Here's an example:

   ```yaml
   logs:
     - type: docker
       source: aws_neuron
       service: aws_neuron
   ```

<!-- xxz tab xxx -->
<!-- xxx tab "Kubernetes" xxx -->

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][13].

Then, set Log Integrations as pod annotations. This can also be configured with a file, a configmap, or a key-value store. For more information, see the configuration section of [Kubernetes Log Collection][14].

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][6] and look for `aws_neuron` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The AWS Neuron integration does not include any events.

### Service Checks

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
[12]: https://docs.datadoghq.com/agent/configuration/agent-configuration-files/#agent-configuration-directory
[13]: https://docs.datadoghq.com/agent/kubernetes/log/#setup
[14]: https://docs.datadoghq.com/agent/kubernetes/log/#configuration
