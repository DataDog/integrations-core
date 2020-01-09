# Agent Check: eks_fargate

## Overview

This check monitors [eks_fargate][1] through the Datadog Agent.

## Setup

### Installation

The eks_fargate check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

Given the nature of AWS EKS Fargate, this check will only run in containerized infrstructures.
To enable it, use the environment variable `DD_EKS_FARGATE=true` in the manifest to deploy your Datadog Agent side care.

### Validation

[Run the Agent's status subcommand][4] and look for `eks_fargate` under the Checks section.

## Data Collected

### Metrics

The eks_fargate check submits a heartbeat metric `eks.fargate.pod.running` that is tagged by `pod_name` and `virtual_node` so you can keep track of how many pods are running.

### Service Checks

eks_fargate does not include any service checks.

### Events

eks_fargate does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][5].

[1]: https://docs.datadoghq.com/integrations/amazon_eks_fargate/?tab=integrationmetrics
[2]: https://github.com/DataDog/integrations-core/blob/master/eks_fargate/datadog_checks/eks_fargate/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[5]: https://docs.datadoghq.com/help
