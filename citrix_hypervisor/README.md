# Agent Check: citrix_hypervisor

## Overview

This check monitors [Citrix Hypervisor][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The Citrix Hypervisor check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.  
The recommended way to monitor Citrix hypervisors is to install one Datadog Agent on each hypervisor.

#### Datadog User

The Citrix Hypervisor integration requires a user with at least [`read-only`][3] access to monitor the service.

### Configuration

#### Host

1. Edit the `citrix_hypervisor.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Citrix Hypervisor performance data. See the [sample citrix_hypervisor.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

#### Log collection

_Available for Agent versions >6.0_

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in `datadog.yaml`:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `citrix_hypervisor.d/conf.yaml` file to start collecting your Citrix Hypervisor logs:
    ```yaml
    logs:
    - type: file
      path: /var/log/xensource.log
      source: citrix_hypervisor
    ```
    Change the `path` value and configure it for your environment. See the [sample `citrix_hypervisor.d/conf.yaml` file][4] for all available configuration options.

3. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `citrix_hypervisor` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this check.

### Events

The Citrix Hypervisor integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://www.citrix.com/products/citrix-hypervisor/
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: https://docs.citrix.com/en-us/xencenter/7-1/rbac-roles.html
[4]: https://github.com/DataDog/integrations-core/blob/master/citrix_hypervisor/datadog_checks/citrix_hypervisor/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/citrix_hypervisor/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/citrix_hypervisor/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
