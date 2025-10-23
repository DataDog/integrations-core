# Agent Check: Proxmox

## Overview

This check monitors [Proxmox][1] through the Datadog Agent. Proxmox is an open-source server management platform. It supports running both VMs and containers. The Proxmox integration collects data about your Proxmox cluster including the status and performance of nodes, VMs, containers, and more.

**Minimum Agent version:** 7.69.0

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

Install the [Datadog Agent][2] and configure the Proxmox integration on one Proxmox node to collect information about your entire Proxmox Cluster. The Proxmox check is included in the [Datadog Agent][2] package. No additional installation is needed on your server.

### Configuration

1. Create an [API Token][10] in your Proxmox Management Interface.
2. Edit the `proxmox.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your proxmox performance data. See the [sample proxmox.d/conf.yaml][4] for all available configuration options. Ensure you have set the following parameters:

    ```
    instances:
    - proxmox_server: http://localhost:8006/api2/json
      headers:
          Authorization: PVEAPIToken=<USER>@<REALM>!<TOKEN_ID>=<YOUR_TOKEN>
    ```

3. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `proxmox` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Logs

To collect logs from all of the Proxmox services on your node:

1. Enable log collection in your `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Uncomment and edit the logs configuration block in your `proxmox.d/conf.yaml` file. For example:

   ```yaml
   logs:
    - type: journald
      source: proxmox
      include_units:
        - pveproxy.service
        - pvedaemon.service
        - pve-firewall.service
        - pve-ha-crm.service
        - pve-ha-lrm.service
        - pvescheduler.service
        - pvestatd.service
        - qmeventd.service
   ```

### Events

The Proxmox integration does not include any events.

### Service Checks

The Proxmox integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://www.proxmox.com
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/proxmox/datadog_checks/proxmox/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/proxmox/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/proxmox/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://pve.proxmox.com/wiki/Proxmox_VE_API#API_Tokens