# Agent Check: TCP connectivity

![Network Graph][9]

## Overview

Monitor TCP connectivity and response time for any host and port.

## Setup

### Installation

The TCP check is included in the [Datadog Agent][1] package, so you don't need to install anything else on any host from which you will probe TCP ports. Though many metrics-oriented checks are best run on the same host(s) as the monitored service, you'll probably want to run this check from hosts that do not run the monitored TCP services, i.e. to test remote connectivity.

### Configuration

Edit the `tcp_check.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][10]. See the [sample tcp_check.d/conf.yaml][2] for all available configuration options:

```
init_config:

instances:
  - name: SSH check
    host: jumphost.example.com # or an IPv4/IPv6 address
    port: 22
    collect_response_time: true # to collect network.tcp.response_time. Default is false.
```

Configuration Options

* `name` (Required) - Name of the service. This will be included as a tag: `instance:<name>`. Note: This tag will have any spaces and dashes converted to underscores.
* `host` (Required) - Host to be checked. This will be included as a tag: `url:<host>:<port>`.
* `port` (Required) - Port to be checked. This will be included as a tag: `url:<host>:<port>`.
* `timeout` (Optional) - Timeout for the check. Defaults to 10 seconds.
* `collect_response_time` (Optional) - Defaults to false. If this is not set to true, no response time metric will be collected. If it is set to true, the metric returned is `network.tcp.response_time`.
* `check_certificate_expiration` (Optional) - When `check_certificate_expiration` is enabled, the service check will check the expiration date of the SSL certificate. Defaults to `false`.
* `days_warning` & `days_critical` (Optional) - When `check_certificate_expiration` is enabled, these settings will raise a warning or critical alert when the SSL certificate is within the specified number of days from expiration.
* `check_hostname` (Optional) - When `check_certificate_expiration` is enabled, this setting will raise a warning if the hostname on the SSL certificate does not match the host of the given URL.
* `ssl_server_name` (Optional) - When `check_certificate_expiration` is enabled, this setting specifies the hostname of the service to connect to and it also overrides the host to match with if check_hostname is enabled.
* `ca_certs` (Optional) - This setting will allow you to override the default certificate path as specified in `init_config`
* `client_key` (Optional) - Path to the TLS client key file
* `client_cert` (Optional) - Path to the TLS client certificate file
* `tags` (Optional) - Tags to be assigned to the metric.

[Restart the Agent][3] to start sending TCP service checks and response times to Datadog.

### Validation

[Run the Agent's `status` subcommand][4] and look for `tcp_check` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this check.

### Events
The TCP check does not include any events at this time.

### Service Checks

**`tcp.can_connect`**:

Returns DOWN if the Agent cannot connect to the configured `host` and `port`, otherwise UP.

**`tcp.ssl_cert`**:

The check returns:

* `DOWN` if the `host`'s certificate has already expired
* `CRITICAL` if the `host`'s certificate expires in less than `days_critical` days
* `WARNING` if the `host`'s certificate expires in less than `days_warning` days

To create alert conditions on this service check in Datadog, click **Network** on the [Create Monitor][6] page, not **Integration**.

## Troubleshooting
Need help? Contact [Datadog support][7].


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/tcp_check/datadog_checks/tcp_check/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/tcp_check/metadata.csv
[6]: https://app.datadoghq.com/monitors#/create
[7]: https://docs.datadoghq.com/help/
[9]: https://raw.githubusercontent.com/DataDog/integrations-core/master/tcp_check/images/netgraphs.png
[10]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
