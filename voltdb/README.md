# Agent Check: VoltDB

## Overview

This check monitors [VoltDB][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

**Note**: This check should only be configured on one Agent per cluster. If you are monitoring a cluster spread across several hosts, install an Agent on each host. However, do not enable the VoltDB integration on more than one host, as this results in duplicate metrics.

### Installation

The VoltDB check is included in the [Datadog Agent][3] package.
No additional installation is needed on your server.

### Configuration

1. Add a `datadog-agent` user. You can do so by editing your VoltDB `deployment.xml` file. **Note**: No specific roles are required, so assign the built-in `user` role.

    ```xml
    <users>
        <!-- ... -->
        <user name="datadog-agent" password="<PASSWORD>" roles="user" />
    </users>
    ```

2. Edit the `voltdb.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your VoltDB performance data. See the [sample voltdb.d/conf.yaml][4] for all available configuration options.

    ```yaml
    init_config:

    instances:
      - url: http://localhost:8080
        username: datadog-agent
        password: "<PASSWORD>"
    ```

3. [Restart the Agent][5].

#### TLS support

If [TLS/SSL][6] is enabled on the client HTTP port:

1. Export your certificate CA file in PEM format:

    ```bash
    keytool -exportcert -file /path/to/voltdb-ca.pem -keystore <KEYSTORE> -storepass <PASSWORD> -alias voltdb -rfc
    ```

1. Export your certificate in PEM format:

    ```bash
    openssl pkcs12 -nodes -in <KEYSTORE> -out /path/to/voltdb.pem -password pass:<PASSWORD>
    ```

    The resulting file should contain the _unencrypted_ private key and the certificate:

    ```
    -----BEGIN PRIVATE KEY-----
    <Private key contents...>
    -----END PRIVATE KEY-----
    -----BEGIN CERTIFICATE-----
    <Certificate contents...>
    -----END CERTIFICATE-----
    ```

2. In your instance configuration, point `url` to the TLS-enabled client endpoint, and set the `tls_cert` and `tls_ca_cert` options. For example:

    ```yaml
    instances:
    - # ...
      url: https://localhost:8443
      tls_cert: /path/to/voltdb.pem
      tls_ca_cert: /path/to/voltdb-ca.pem
    ```

3. [Restart the Agent][5].

#### Log collection

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

    ```yaml
    logs_enabled: true
    ```

2. Add this configuration block to your `voltdb.d/conf.yaml` file to start collecting your VoltDB logs:

    ```yaml
    logs:
      - type: file
        path: /var/log/voltdb.log
        source: voltdb
    ```

  Change the `path` value based on your environment. See the [sample `voltdb.d/conf.yaml` file][4] for all available configuration options.

  3. [Restart the Agent][5].

  To enable logs for Kubernetes environments, see [Kubernetes Log Collection][7].

### Validation

[Run the Agent's status subcommand][8] and look for `voltdb` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][9] for a list of metrics provided by this check.

### Events

This check does not include any events.

### Service Checks

See [service_checks.json][10] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][11].

## Further Reading

{{< partial name="whats-next/whats-next.html" >}}

[1]: https://voltdb.com
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: https://app.datadoghq.com/account/settings/agent/latest
[4]: https://github.com/DataDog/integrations-core/blob/master/voltdb/datadog_checks/voltdb/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.voltdb.com/UsingVoltDB/SecuritySSL.php
[7]: https://docs.datadoghq.com/agent/kubernetes/log/
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/voltdb/metadata.csv
[10]: https://github.com/DataDog/integrations-core/blob/master/voltdb/assets/service_checks.json
[11]: https://docs.datadoghq.com/help/
