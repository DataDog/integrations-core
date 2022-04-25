# Podman Integration

[Podman][1] is a daemonless container engine for developing, managing, and running OCI Containers on your Linux System. Containers can either be run as root or in rootless mode.

## Overview

Podman container runtime is supported by the [container Agent check][2].
This check reports a set of metrics on any running containers, regardless of the runtime used to start them.

**NOTE**: The `container` check report standardizes metrics for all containers found on the system, regardless of the container runtime.

## Setup

### Installation

To monitor containers managed by [Podman][1], see the [installation instructions][3] for the [container Agent check][2].

## Data Collected

### Metrics

See [metadata.csv][4] for a list of metrics provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][1].

[1]: https://podman.io/
[2]: https://docs.datadoghq.com/integrations/container/
[3]: https://docs.datadoghq.com/integrations/container/#setup
[4]: https://github.com/DataDog/integrations-core/blob/master/container/metadata.csv
