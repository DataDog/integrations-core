# Agent Check: {integration_name}

## Overview

This check monitors [{integration_name}][1].

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

2. Add this configuration block to your `{check_name}.d/conf.yaml` file to start collecting your DataNode logs:

    ```yaml
      logs:
        - type: file
          path:  /var/log/{check_name}.log
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

[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
