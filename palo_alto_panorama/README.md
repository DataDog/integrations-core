# Agent Integration: palo-alto-panorama

## Overview

This integration monitors [palo-alto-panorama][4].

## Setup

### Installation

The palo-alto-panorama check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. <List of steps to setup this Integration>

### Validation

<Steps to validate integration is functioning as expected>

## Data Collected

### Metrics

palo-alto-panorama does not include any metrics.

### Log Collection


1. Collecting logs is disabled by default in the Datadog Agent. Enable it in the `datadog.yaml` file with:

    ```yaml
      logs_enabled: true
    ```

2. Add this configuration block to your `palo_alto_panorama.d/conf.yaml` file to start collecting your palo-alto-panorama logs:

    ```yaml
      logs:
        - type: file
          path:  /var/log/palo-alto-panorama.log
          source: palo_alto_panorama
          service: <SERVICE_NAME>
    ```

    Change the `path` and `service` parameter values and configure them for your environment.

3. [Restart the Agent][3].

### Events

The palo-alto-panorama integration does not include any events.

### Service Checks

The palo-alto-panorama integration does not include any service checks.

See [service_checks.json][5] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[4]: **LINK_TO_INTEGRATION_SITE**
[5]: https://github.com/DataDog/integrations-core/blob/master/palo_alto_panorama/assets/service_checks.json
