# Windows Registry Integration

## Overview

Watch for changes in Windows Registry keys and forward them to Datadog. Enable this integration to:

- Understand system and application level health and state through Windows Registry values.
- Monitor for unexpected changes impacting security and compliance requirements.

## Setup

### Installation

The Windows Registry integration is included in the [Datadog Agent][1] package. No additional installation is needed.

### Configuration

This integration collects and reports Windows Registry information using both of the following methods:

- As [Datadog Metrics][2]
- As [Datadog Logs][3]


1. Edit the `windows_registry.d/conf.yaml` file in the `conf.d/` folder at the root of your Agent's [configuration directory][4] to start collecting Windows registry information. See the [sample windows_registry.d/conf.yaml][5] for all available configuration options.

2. To send registry values and changes as Logs, log collection needs to be enabled in the Datadog Agent. To enable log collection, add the following to your `datadog.yaml` file: 

    ```yaml
    logs_enabled: true
    ```

3. [Restart the Agent][6].


### Validation

Check the information page in the Datadog Agent Manager or run the Agent's `status` [subcommand][7] and look for `windows_registry` under the **Checks** section.

## Data Collected

### Metrics

All metrics collected by the Windows Registry integration are forwarded to Datadog as [custom metrics][11], which may impact your billing.

### Logs

All logs collected by the Windows Registry integration are forwarded to Datadog, and are subject to [Logs billing][8].

### Service Checks

The Windows Registry integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][9] with an [Agent Flare][10].

[1]: https://app.datadoghq.com/account/settings/agent/latest?platform=windows
[2]: https://docs.datadoghq.com/metrics/#overview
[3]: https://docs.datadoghq.com/logs/
[4]: https://docs.datadoghq.com/agent/configuration/agent-configuration-files/?tab=agentv6v7#agent-configuration-directory
[5]: https://github.com/DataDog/datadog-agent/blob/main/cmd/agent/dist/conf.d/windows_registry.d/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#restart-the-agent
[7]: https://docs.datadoghq.com/agent/basic_agent_usage/windows/?tab=gui#agent-status-and-information
[8]: https://docs.datadoghq.com/account_management/billing/log_management/
[9]: https://docs.datadoghq.com/help/
[10]:https://docs.datadoghq.com/agent/troubleshooting/send_a_flare/?tab=agentv6v7
[11]:https://docs.datadoghq.com/account_management/billing/custom_metrics/?tab=countrate
