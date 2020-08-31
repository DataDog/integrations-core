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
docker exec -it iot-edge-device iotedge -H "http://$(docker inspect iot-edge-device -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'):15580" logs -f SimulatedTemperatureSensor
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
