# Agent Check: Nvidia NVML

## Overview

This check monitors [NVIDIA Management Library (NVML)][1] exposed metrics through the Datadog Agent and can correlate them with the [exposed Kubernetes devices][12].

## Setup

The NVML check is not included in the [Datadog Agent][2] package, so you need to install it.

### Installation

For Agent v7.21+ / v6.21+, follow the instructions below to install the NVML check on your host. See [Use Community Integrations][3] to install with the Docker Agent or earlier versions of the Agent.

1. Run the following command to install the Agent integration:

   ```shell
   datadog-agent integration install -t datadog-nvml==<INTEGRATION_VERSION>
   # You may also need to install dependencies since those aren't packaged into the wheel
   sudo -u dd-agent -H /opt/datadog-agent/embedded/bin/pip3 install grpcio pynvml
   ```

2. Configure your integration similar to core [integrations][4].

If you are using Docker, there is an [example Dockerfile][15] in the NVML repository.

   ```shell
   docker build -t dd-agent-nvml .
   ```

If you're using Docker and Kubernetes, you need to expose the environment variables `NVIDIA_VISIBLE_DEVICES` and `NVIDIA_DRIVER_CAPABILITIES`. See the included Dockerfile for an example.

To correlate reserved Kubernetes NVIDIA devices with the Kubernetes pod using the device, mount the Unix domain socket `/var/lib/kubelet/pod-resources/kubelet.sock` into your Agent's configuration. More information about this socket is on the [Kubernetes website][12]. **Note**: This device is in beta support for version 1.15.

### Configuration

1. Edit the `nvml.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your NVML performance data. See the [sample nvml.d/conf.yaml][7] for all available configuration options.

2. [Restart the Agent][8].

### Validation

[Run the Agent's status subcommand][9] and look for `nvml` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][10] for a list of metrics provided by this check. The authoritative metric documentation is on the [NVIDIA website][13].

There is an attempt to, when possible, match metric names with NVIDIA's [Data Center GPU Manager (DCGM) exporter][14].

### Events

NVML does not include any events.

### Service Checks

See [service_checks.json][16] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][11].


[1]: https://pypi.org/project/pynvml/
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/use-community-integrations/
[4]: https://docs.datadoghq.com/getting_started/integrations/
[7]: https://github.com/DataDog/integrations-extras/blob/master/nvml/datadog_checks/nvml/data/conf.yaml.example
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[10]: https://github.com/DataDog/integrations-extras/blob/master/nvml/metadata.csv
[11]: https://docs.datadoghq.com/help
[12]: https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/device-plugins/#monitoring-device-plugin-resources
[13]: https://docs.nvidia.com/deploy/nvml-api/group__nvmlDeviceQueries.html
[14]: https://github.com/NVIDIA/dcgm-exporter
[15]: https://github.com/DataDog/integrations-extras/blob/master/nvml/tests/Dockerfile
[16]: https://github.com/DataDog/integrations-extras/blob/master/nvml/assets/service_checks.json
