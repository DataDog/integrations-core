# Agent Integration: cisco-secure-firewall

## Overview

This integration monitors [cisco-secure-firewall][4].

## Setup

### Installation

The cisco-secure-firewall check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. <List of steps to setup this Integration>

### Validation

<Steps to validate integration is functioning as expected>

## Data Collected

### Metrics

cisco-secure-firewall does not include any metrics.

### Log Collection


1. Collecting logs is disabled by default in the Datadog Agent. Enable it in the `datadog.yaml` file with:

    ```yaml
      logs_enabled: true
    ```

2. Add this configuration block to your `cisco_secure_firewall.d/conf.yaml` file to start collecting your cisco-secure-firewall logs:

    ```yaml
      logs:
        - type: file
          path:  /var/log/cisco-secure-firewall.log
          source: cisco-secure-firewall
          service: cisco-secure-firewall
    ```

    Change the `path` and `service` parameter values and configure them for your environment.

3. [Restart the Agent][3].

### Events

The cisco-secure-firewall integration does not include any events.

### Service Checks

The cisco-secure-firewall integration does not include any service checks.

See [service_checks.json][5] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[4]: **LINK_TO_INTEGRATION_SITE**
[5]: https://github.com/DataDog/integrations-core/blob/master/cisco_secure_firewall/assets/service_checks.json
