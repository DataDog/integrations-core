# Agent Integration: Trend Micro Cloud One

## Overview

This integration monitors [Trend Micro Cloud One][4].

## Setup

### Installation

The Trend Micro Cloud One check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

!!! Add list of steps to set up this integration !!!

### Validation

!!! Add steps to validate integration is functioning as expected !!!

## Data Collected

### Metrics

Trend Micro Cloud One does not include any metrics.

### Log Collection


1. Collecting logs is disabled by default in the Datadog Agent. Enable it in the `datadog.yaml` file with:

    ```yaml
      logs_enabled: true
    ```

2. Add this configuration block to your `trend_micro_cloud_one.d/conf.yaml` file to start collecting your Trend Micro Cloud One logs:

    ```yaml
      logs:
        - type: file
          path:  /var/log/Trend Micro Cloud One.log
          source: trend_micro_cloud_one
          service: <SERVICE_NAME>
    ```

    Change the `path` and `service` parameter values and configure them for your environment.

3. [Restart the Agent][3].

### Events

The Trend Micro Cloud One integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[4]: **LINK_TO_INTEGRATION_SITE**
[5]: https://github.com/DataDog/integrations-core/blob/master/trend_micro_cloud_one/assets/service_checks.json

