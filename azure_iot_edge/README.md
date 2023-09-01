# Agent Check: Azure IoT Edge

## Overview

[Azure IoT Edge][1] is a fully managed service to deploy Cloud workloads to run on Internet of Things (IoT) Edge devices using standard containers.

Use the Datadog-Azure IoT Edge integration to collect metrics and health status from IoT Edge devices.

**Note**: This integration requires IoT Edge runtime version 1.0.10 or above.

## Setup

Follow the instructions below to install and configure this check for an IoT Edge device running on a device host.

### Installation

The Azure IoT Edge check is included in the [Datadog Agent][2] package.

No additional installation is needed on your device.

### Configuration

Configure the IoT Edge device so that the Agent runs as a custom module. Follow the Microsoft documentation on [deploying Azure IoT Edge modules][3] for information on installing and working with custom modules for Azure IoT Edge.

Follow the steps below to configure the IoT Edge device, runtime modules, and the Datadog Agent to start collecting IoT Edge metrics.

1. Configure the **Edge Agent** runtime module as follows:
    - Image version must be `1.0.10` or above.
    - Under "Create Options", add the following `Labels`. Edit the `com.datadoghq.ad.instances` label as appropriate. See the [sample azure_iot_edge.d/conf.yaml][4] for all available configuration options. See the documentation on [Docker Integrations Autodiscovery][5] for more information on labels-based integration configuration.

        ```json
        "Labels": {
            "com.datadoghq.ad.check_names": "[\"azure_iot_edge\"]",
            "com.datadoghq.ad.init_configs": "[{}]",
            "com.datadoghq.ad.instances": "[{\"edge_hub_prometheus_url\": \"http://edgeHub:9600/metrics\", \"edge_agent_prometheus_url\": \"http://edgeAgent:9600/metrics\"}]"
        }
        ```

2. Configure the **Edge Hub** runtime module as follows:
    - Image version must be `1.0.10` or above.

3. Install and configure the Datadog Agent as a **custom module**:
    - Set the module name. For example: `datadog-agent`.
    - Set the Agent image URI. For example: `datadog/agent:7`.
    - Under "Environment Variables", configure your `DD_API_KEY`. You may also set extra Agent configuration here (see [Agent Environment Variables][6]).
    - Under "Container Create Options", enter the following configuration based on your device OS. **Note**: `NetworkId` must correspond to the network name set in the device `config.yaml` file.

        - Linux:
            ```json
            {
                "HostConfig": {
                    "NetworkMode": "default",
                    "Env": ["NetworkId=azure-iot-edge"],
                    "Binds": ["/var/run/docker.sock:/var/run/docker.sock"]
                }
            }
            ```
        - Windows:
            ```json
            {
                "HostConfig": {
                    "NetworkMode": "default",
                    "Env": ["NetworkId=nat"],
                    "Binds": ["//./pipe/iotedge_moby_engine:/./pipe/docker_engine"]
                }
            }
            ```

    - Save the Datadog Agent custom module.

4. Save and deploy changes to your device configuration.

#### Log collection

1. Collecting logs is disabled by default in the Datadog Agent, enable it by configuring your Datadog Agent custom module:
    - Under "Environment Variables", set the `DD_LOGS_ENABLED` environment variable:

        ```yaml
        DD_LOGS_ENABLED: true
        ```

2. Configure the **Edge Agent** and **Edge Hub** modules: under "Create Options", add the following label:

    ```json
    "Labels": {
        "com.datadoghq.ad.logs": "[{\"source\": \"azure.iot_edge\", \"service\": \"<SERVICE>\"}]",
        "...": "..."
    }
    ```

    Change the `service` based on your environment.

    Repeat this operation for any custom modules you'd like to collect logs for.

3. Save and deploy changes to your device configuration.

### Validation

Once the Agent has been deployed to the device, [run the Agent's status subcommand][7] and look for `azure_iot_edge` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this check.

### Events

Azure IoT Edge does not include any events.

### Service Checks

See [service_checks.json][9] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][10].

## Further Reading

- [Monitor Azure IoT Edge with Datadog][11]

[1]: https://azure.microsoft.com/en-us/services/iot-edge/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.microsoft.com/en-us/azure/iot-edge/how-to-deploy-modules-portal
[4]: https://github.com/DataDog/integrations-core/blob/master/azure_iot_edge/datadog_checks/azure_iot_edge/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/docker/integrations/
[6]: https://docs.datadoghq.com/agent/guide/environment-variables/
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/azure_iot_edge/metadata.csv
[9]: https://github.com/DataDog/integrations-core/blob/master/azure_iot_edge/assets/service_checks.json
[10]: https://docs.datadoghq.com/help/
[11]: https://www.datadoghq.com/blog/monitor-azure-iot-edge-with-datadog/
