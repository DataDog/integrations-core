## Overview

This integration monitors [Tenable Nessus][1] logs through the Datadog Agent.

## Setup

Follow the instructions below configure this integration for an Agent running on a host.

### Installation

To install the Tenable integration configuration on your Agent:

**Note**: This step will not be necessary for Agent version >= 7.18.0.

1. [Install][2] the 1.0 release (`tenable==1.0.0`).

### Configuration

The Agent tails the Tenable Nessus `webserver` and `backend` logs to collect data on Nessus scans.

#### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Uncomment and edit this configuration block at the bottom of your `tenable.d/conf.yaml`:

   See the [sample tenable.d/conf.yaml][3] for available configuration options.

   ```yaml
   logs:
    - type: file
      path: /opt/nessus/var/nessus/logs/backend.log
      service: nessus_backend
      source: tenable

    - type: file
      path: /opt/nessus/var/nessus/logs/www_server.log
      service: nessus_webserver
      source: tenable
   ```

    Customize the `path` and `service` parameter values if necessary for your environment.

3. [Restart the Agent][7].


#### Log Data collected

1. Nessus backend logs collect data on scan names, start time, stop time, durations, target(s)
2. Nessus webserver logs collect data on access logs for neesus webserver including Client IPs, User agents, login attempt/success/failure.


### Metrics

This integration does not include any metrics.

### Events

This integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][5].

[1]: https://www.tenable.com/products/nessus
[2]: https://docs.datadoghq.com/agent/guide/integration-management/#install
[3]: https://github.com/DataDog/integrations-core/blob/master/tenable/datadog_checks/tenable/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/help
