# Azure IoT Edge E2E Setup

## Credits

This test setup was adapted from: https://github.com/Azure/iotedgedev/tree/v2.1.4/docker/runtime

## Building from RCs

RCs for the Azure IoT Edge runtime are not available on standard package managers, so the build is done against GitHub release assets directly.

See: https://docs.microsoft.com/en-us/azure/iot-edge/how-to-install-iot-edge-linux#install-runtime-using-release-assets

## Use IoT Edge CLI

Once the container is running, you can interact with the IoT Edge daemon like so:

```bash
docker exec iot-edge-device iotedge -H http://<CONTAINER_IP>:15580 <command>
```

For example, to list the active IoT Edge modules:

```bash
docker exec iot-edge-device iotedge -H "http://$(docker inspect iot-edge-device -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'):15580" list
```

## Simulated temperature sensor

The `SimulatedTemperatureSensor` is enabled in the environment.

To view simulated data, run:

```bash
docker logs -f SimulatedTemperatureSensor
```

## Logs collection

To send integration logs to Staging US, edit your `ddev` configuration with:

```toml
[orgs.staging-us]
api_key = "<STAGING_API_KEY>"
logs_url = "<STAGING_AGENT_INTAKE_HOSTNAME>"
```

Then start the environment using `-o staging-us`.

Validate that logs are being sent by inspecting the logs section of `docker exec -it <agent_container_name> agent status`.

## Generate mock server metrics

The data in [`metrics/`](./compose/device/mock_server/metrics) was generated as follows:

* Start an E2E environment.
* Let it run for a few minutes.
* Generate metrics files:

```bash
curl localhost:9601/metrics > azure_iot_edge/tests/compose/mock_server/metrics/edge_hub.txt
curl localhost:9602/metrics > azure_iot_edge/tests/compose/mock_server/metrics/edge_agent.txt
```

* Manually edit `edge_agent.txt` (replace `<INSTANCE_NUMBER>` with the instance number from the output):
  * Add a value line for `edgeAgent_unsuccessful_iothub_syncs_total` (no way to trigger unsuccessful syncs were found):

    ```
    edgeAgent_unsuccessful_iothub_syncs_total{iothub="iot-edge-dev-hub.azure-devices.net",edge_device="testEdgeDevice",instance_number="c2c90030-2df4-4c92-98cb-deaa9ef05cac",ms_telemetry="True"} 0
    ```

  * Add value lines for `edgeAgent_module_stop_total`:

    ```
    edgeAgent_module_stop_total{iothub="iot-edge-dev-hub.azure-devices.net",edge_device="testEdgeDevice",instance_number="c2c90030-2df4-4c92-98cb-deaa9ef05cac",module_name="SimulatedTemperatureSensor",module_version="1.0",ms_telemetry="True"} 0
    edgeAgent_module_stop_total{iothub="iot-edge-dev-hub.azure-devices.net",edge_device="testEdgeDevice",instance_number="c2c90030-2df4-4c92-98cb-deaa9ef05cac",module_name="edgeHub",module_version="",ms_telemetry="True"} 0
    ```

  * Add value lines for `edgeAgent_total_disk_space_bytes` (containers don't have individual disks):

    ```
    edgeAgent_total_disk_space_bytes{iothub="iot-edge-dev-hub.azure-devices.net",edge_device="testEdgeDevice",instance_number="c2c90030-2df4-4c92-98cb-deaa9ef05cac",module_name="edgeAgent",ms_telemetry="True"} 1073741824
    edgeAgent_total_disk_space_bytes{iothub="iot-edge-dev-hub.azure-devices.net",edge_device="testEdgeDevice",instance_number="c2c90030-2df4-4c92-98cb-deaa9ef05cac",module_name="edgeHub",ms_telemetry="True"} 1073741824
    edgeAgent_total_disk_space_bytes{iothub="iot-edge-dev-hub.azure-devices.net",edge_device="testEdgeDevice",instance_number="c2c90030-2df4-4c92-98cb-deaa9ef05cac",module_name="SimulatedTemperatureSensor",ms_telemetry="False"} 1073741824
    ```

* Manually edit `edge_hub.txt` (replace `<INSTANCE_NUMBER>` with the instance number from the output):
  * Edit any `NaN` values so that all metrics report correctly.
  * Add a value line for `edgehub_dropped_total`:

    ```
    edgehub_messages_dropped_total{iothub="iot-edge-dev-hub.azure-devices.net",edge_device="testEdgeDevice",instance_number="<INSTANCE_NUMBER>",from="testEdgeDevice/SimulatedTemperatureSensor",from_route_output="temperatureOutput",reason="ttl_expiry",ms_telemetry="True"} 1
    ```

  * Add a value line for `edgehub_offline_count_total`:

    ```
    edgehub_offline_count_total{iothub="iot-edge-dev-hub.azure-devices.net",edge_device="testEdgeDevice",instance_number="<INSTANCE_NUMBER>",id="testEdgeDevice/$edgeHub",ms_telemetry="True"} 1
    ```

  * Add a definition and value for the `edgehub_messages_unack_total` metric (no way to trigger storage failures locally was found):

    ```
    # HELP edgehub_messages_unack_total Total number of messages unack because storage failure
    # TYPE edgehub_messages_unack_total counter
    edgehub_messages_unack_total{iothub="iot-edge-dev-hub.azure-devices.net",edge_device="testEdgeDevice",instance_number="<INSTANCE_NUMBER>",from="testEdgeDevice/SimulatedTemperatureSensor",from_route_output="temperatureOutput",reason="storage_failure",ms_telemetry="True"} 1
    ```

  * Add a definition and value for the `edgehub_operation_retry_total` metric (no way to trigger them locally was found):

    ```
    # HELP edgehub_operation_retry_total Total number of times edgeHub operations were retried
    # TYPE edgehub_operation_retry_total counter
    edgehub_operation_retry_total{iothub="iot-edge-dev-hub.azure-devices.net",edge_device="testEdgeDevice",instance_number="<INSTANCE_NUMBER>",id="testEdgeDevice/$edgeHub",operation="test",ms_telemetry="True"} 1
    ```

  * Add a definition and value for the `edgehub_client_connect_failed_total` metric (we do not have auth set up yet):

    ```
    # HELP edgehub_client_connect_failed_total Total number of times clients failed to connect to edgeHub
    # TYPE edgehub_client_connect_failed_total counter
    edgehub_client_connect_failed_total{iothub="iot-edge-dev-hub.azure-devices.net",edge_device="testEdgeDevice",instance_number="0dab21d7-d0de-4527-99df-27c8e5861eac",id="testEdgeDevice/SimulatedTemperatureSensor",reason="not_authenticated",ms_telemetry="True"} 1
    ```

## Troubleshooting

Guides:

* https://docs.microsoft.com/en-us/azure/iot-edge/troubleshoot-common-errors
* https://docs.microsoft.com/en-us/azure/iot-edge/troubleshoot

In particular, you can run a `check` command in the `iot-edge-device` container to check for any configuration or connectivity issues:

```bash
$ docker exec -it iot-edge-device iotedge -H "http://$(docker inspect iot-edge-device -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'):15580" check
Configuration checks
--------------------
√ config.yaml is well-formed - OK
√ config.yaml has well-formed connection string - OK
√ container engine is installed and functional - OK
× config.yaml has correct hostname - Error
    config.yaml has hostname edgehub but device reports hostname 0504777ae8c2.
    Hostname in config.yaml must either be identical to the device hostname or be a fully-qualified domain name that has the device hostname as the first component.
× config.yaml has correct URIs for daemon mgmt endpoint - Error
    Error: could not execute list-modules request: an error occurred trying to connect: Connection refused (os error 111)
...
```
