# azure_iot_edge certs

Files in this directory were created following the [Create demo certificates to test IoT Edge device features](https://docs.microsoft.com/en-us/azure/iot-edge/how-to-create-test-certificates) guide.

They aim at testing the integration works well with devices that are provisioned using X.509 certificates (such that communication between IoT Edge components is encrypted using TLS).

## Generate E2E test TLS certificates

To regenerate certificates for your own E2E testing, run the setup script:

```bash
./azure_iot_edge/tests/tls/setup.sh
```

This script will prompt you to:

* Upload a test root CA to the IoT Hub web UI. (Note that these certs expire after 30 days. After this period of time, you would need to go through this procedure again to do E2E testing.)
* Generate a verification code in the IoT Hub web UI, and enter it in the CLI.
* Upload the generated verification cert to IoT Hub web UI.
* Eventually the cert should show as "Verified" in the IoT Hub web UI.
* Make sure not to modify any filename for the generated files, since the `-tls` E2E environments rely on them.

## Misc

The following files were taken from https://github.com/Azure/azure-iot-sdk-c/tree/master/tools/CACertificates:

```
certGen.ssh
openssl_root_ca.cnf
openssl_device_intermediate_ca.cnf
```
