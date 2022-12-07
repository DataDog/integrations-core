# Agent Check: Container

## Overview

This check reports a set of metrics about any running containers, regardless of the runtime used to start them.

**NOTE**: The `container` check is different from the `containerd` check. The `container` checks report standardized metrics for all containers found on the system, regardless of the container runtime.
The `containerd` is dedicated to `containerd` runtime and publishes metrics in the `containerd.*` namespace.

## Setup

### Installation

Container is a core Datadog Agent check and is automatically activated if any supported container runtime is detected.
Configuring access to supported container runtimes (Docker, containerd) may be required depending on your environment.

#### Installation on containers

The `container` check requires some folders to be mounted to allow for automatic activation. This is handled by the official Helm Chart, the Datadog Operator, and as documented set ups for Kubernetes, Docker, ECS, and ECS Fargate.

### Configuration

The `container` check does not expose any specific configuration settings. To customize common fields or to force the activation of the `container` check, follow these steps:

1. Create the `container.d/conf.yaml` file in the `conf.d/` folder at the root of your Agent's configuration directory.

2. [Restart the Agent][2]

The `container` check can collect metrics about CPU, Memory, Network and Disks IO.
Some metrics may not be available depending on your environment (Linux / Windows, for instance).

### Validation

[Run the Agent's `status` subcommand][2] and look for `container` under the **Checks** section.

## Data Collected

### Metrics

See [metadata.csv][3] for a list of metrics provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[3]: https://github.com/DataDog/integrations-core/blob/master/container/metadata.csv
