# DNS Integration

## Overview

Monitor the resolvability of and lookup times for any DNS records using nameservers of your choosing.

## Setup

### Installation

The DNS check is included in the [Datadog Agent][1] package, so you don't need to install anything else on the server from which you will probe your DNS servers.

Though many metrics-oriented checks are best run on the same host(s) as the monitored service, you may want to run this status-oriented check from hosts that do not run the monitored DNS services.

### Configuration

1. Edit the `dns_check.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][7] to start collecting your Couchbase performance data.
    See the [sample dns_check.d/conf.yaml][2] for all available configuration options:

    ```yaml
      init_config:

      instances:
        - name: Example (com)
          # nameserver: 8.8.8.8   # The nameserver to query, this must be an IP address
          hostname: example.com # the record to fetch
          # record_type: AAAA   # default is A
        - name: Example (org)
          hostname: example.org
    ```

    If you omit the `nameserver` option, the check uses whichever nameserver is configured in local network settings.

2. [Restart the Agent][3] to begin sending DNS service checks and response times to Datadog.

### Validation

[Run the Agent's `status` subcommand][4] and look for `dns_check` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

### Events
The DNS check does not include any events at this time.

### Service Checks
This agent check tags all service checks it collects with:

  * `nameserver:<nameserver_in_yaml>`
  * `resolved_hostname:<hostname_in_yaml>`

`dns.can_resolve`:

Returns CRITICAL if the Agent fails to resolve the request, otherwise returns UP.

Tagged by `hostname` and `record_type`.

## Troubleshooting
Need help? Contact [Datadog Support][6].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/dns_check/datadog_checks/dns_check/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/dns_check/metadata.csv
[6]: https://docs.datadoghq.com/help/
[7]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
