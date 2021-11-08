# Agent Check: Containerd

## Overview

This check reports a set of metrics about any running containers, regardless of the runtime used to start them.

## Setup

### Installation

Container is a core Agent 6 check and is automatically activated if any supported container runtime is detected.
Configuring access to supported container runtimes (Docker, containerd) may be required depending on your environment.

#### Installation on containers

The `container` check requires some folders to be mounted to allow for automatic activation. This is handled by our official Helm Chart, the Datadog Operator as well as documented setups for Kubernetes, Docker, ECS and ECS Fargate.

### Configuration

Currently, the `container` check does not expose any specific configuration setting. However to customize common fields or to force the activation of the `container` check, follow these steps:

1. Create the `container.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory.

2. [Restart the Agent][2]

### Validation

[Run the Agent's `status` subcommand][3] and look for `container` under the Checks section.

## Data Collected

### Metrics

The `container` check can collect metrics about CPU, Memory, Network and Disks IO.
Some metrics may not be available depending on your environment (Linux / Windows, for instance).

See [metadata.csv][4] for a list of metrics provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][2].

[2]: https://docs.datadoghq.com/help/
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[4]: https://github.com/DataDog/integrations-core/blob/master/container/metadata.csv
