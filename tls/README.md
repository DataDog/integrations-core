# Agent Check: TLS

## Overview

This check monitors [TLS][1] protocol versions, certificate expiration & validity, etc.

## Setup

### Installation

The TLS check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `tls.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your TLS data. See the [sample tls.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4].

### Validation

[Run the Agent's status subcommand][5] and look for `tls` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this integration.

### Service Checks

See [service_checks.json][7] for a list of service checks provided by this integration.

- `tls.can_connect` - Returns `CRITICAL` if the Agent is unable to connect to the monitored endpoint, otherwise returns `OK`.
- `tls.version` - Returns `CRITICAL` if a connection is made with a protocol version that is not allowed, otherwise returns `OK`.
- `tls.cert_validation` - Returns `CRITICAL` if the certificate is malformed or does not match the server hostname, otherwise returns `OK`.
- `tls.cert_expiration` - Returns `CRITICAL` if the certificate has expired or expires in less than `days_critical`, returns `WARNING` if the certificate expires in less than `days_warning`, otherwise returns `OK`.

### Events

TLS does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://en.wikipedia.org/wiki/Transport_Layer_Security
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://github.com/DataDog/integrations-core/blob/master/tls/datadog_checks/tls/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/tls/metadata.csv
[7]: https://github.com/DataDog/integrations-core/blob/master/tls/service_checks.json
[8]: https://docs.datadoghq.com/help
