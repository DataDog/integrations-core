# Agent Integration: {integration_name}

## Overview

This integration monitors [{integration_name}][3].

## Setup

### Installation

{install_info}

### Configuration

1. <List of steps to setup this Integration>

### Validation

<Steps to validate integration is functioning as expected>

## Data Collected

### Metrics

{integration_name} does not include any metrics.

### Log Collection


1. Collecting logs is disabled by default in the Datadog Agent. Enable it in the `datadog.yaml` file with:

    ```yaml
      logs_enabled: true
    ```

2. Add this configuration block to your `{check_name}.d/conf.yaml` file to start collecting your {integration_name} logs:

    ```yaml
      logs:
        - type: file
          path:  /var/log/{integration_name}.log
          source: {check_name}
          service: <SERVICE_NAME>
    ```

    Change the `path` and `service` parameter values and configure them for your environment.

3. [Restart the Agent][2].

### Service Checks

{integration_name} does not include any service checks.

### Events

{integration_name} does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[3]: **LINK_TO_INTEGRATION_SITE**
