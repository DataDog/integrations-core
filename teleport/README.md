# Agent Check: Teleport

## Overview

This integration monitors the health and performance of [Teleport][1] through the Datadog Agent. Enable this integration to:

- Quickly understand the operational status of your Teleport cluster, including the Auth, Proxy, SSH, database, and Kubernetes services.
- Query and audit user sessions that connect to Kubernetes and database services to identify rogue or compromised users in your organization.
- Cluster logs into patterns for faster investigation of abnormal infrastructure access, such as a high number of failed logins or attempts to access as many resources as possible in a short period of time.


## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Teleport integration is included in the Datadog Agent package. No additional installation is needed on your server.

### Prerequisites

The Teleport check gathers Teleport's metrics and performance data using two distinct endpoints:

- The [Health endpoint](https://goteleport.com/docs/management/diagnostics/monitoring/#healthz) provides the overall health status of your Teleport instance.
- The [OpenMetrics endpoint](https://goteleport.com/docs/reference/metrics/#auth-service-and-backends) extracts metrics on the Teleport instance and the various services operating within that instance.

These endpoints aren't activated by default. To enable the diagnostic HTTP endpoints in your Teleport instance, please refer to the public Teleport [documentation](https://goteleport.com/docs/management/diagnostics/monitoring/#enable-health-monitoring).

### Configuration

##### Metric collection

1. Edit the `teleport.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your teleport performance data. See the [sample teleport.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

##### Log collection

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Edit the `logs` section of your `teleport.d/conf.yaml` file to start collecting your Teleport logs:

   ```yaml
   logs:
     - type: file
       path: /var/log/teleport/teleport.log
       source: teleport
       service: telepor-service
      log_processing_rules:
         - type: multi_line
         name: logs_start_with_date
         pattern: \d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01])
   ```

3. [Restart the Agent][8].

### Validation

[Run the Agent's status subcommand][6] and look for `teleport` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Teleport integration does not include any events.

### Service Checks

The Teleport integration does not include any service checks.

## Further reading

Additional helpful documentation, links, and articles:

- [Monitor Teleport with Datadog][10]

## Troubleshooting

Need help? Contact [Datadog support][9].

[1]: https://goteleport.com/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/teleport/datadog_checks/teleport/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/teleport/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/teleport/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://www.datadoghq.com/blog/teleport-integration/
