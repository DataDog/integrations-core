# Agent Check: TLS

## Overview

This check monitors [TLS][1] protocol versions, certificate expiration and validity, etc.

**Notes**:

1. Only TCP is supported.
2. Only leaf / end user certificates are verified (not intermediate and root certificates).

## Setup

### Installation

The TLS check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

1. Edit the `tls.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your TLS data. See the [sample tls.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][9] for guidance on applying the parameters below.

| Parameter            | Value                                  |
| -------------------- | -------------------------------------- |
| `<INTEGRATION_NAME>` | `tls`                                  |
| `<INIT_CONFIG>`      | blank or `{}`                          |
| `<INSTANCE_CONFIG>`  | `{"server": "%%host%%", "port":"443"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][5] and look for `tls` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this integration.

### Events

TLS does not include any events.

### Service Checks

See [service_checks.json][7] for a list of service checks provided by this integration:

**tls.can_connect**:<br>
Returns `CRITICAL` if the Agent is unable to connect to the monitored endpoint, otherwise returns `OK`.

**tls.version**:<br>
Returns `CRITICAL` if a connection is made with a protocol version that is not allowed, otherwise returns `OK`.

**tls.cert_validation**:<br>
Returns `CRITICAL` if the certificate is malformed or does not match the server hostname, otherwise returns `OK`.

**tls.cert_expiration**:<br>
Returns `CRITICAL` if the certificate has expired or expires in less than `days_critical`/`seconds_critical`, returns `WARNING` if the certificate expires in less than `days_warning`/`seconds_warning`, otherwise returns `OK`.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://en.wikipedia.org/wiki/Transport_Layer_Security
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://github.com/DataDog/integrations-core/blob/master/tls/datadog_checks/tls/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/tls/metadata.csv
[7]: https://github.com/DataDog/integrations-core/blob/master/tls/assets/service_checks.json
[8]: https://docs.datadoghq.com/help/
[9]: https://docs.datadoghq.com/agent/kubernetes/integrations/
