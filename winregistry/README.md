# Windows Registry Integration (Beta)

## Overview

Watch for changes in Windows Registry keys and forward them to Datadog. Enable this integration to:

- Understand system and application health through Windows Registry key values
- Monitor for unexpected changes impacting security and compliance requirements

## Setup

### Installation

The Windows Crash Detection integration is included in the [Datadog Agent][1] package. No additional installation is needed.

### Configuration

This integration collects Windows Registry information using one or both of the following methods:

- As [Datadog Metrics][2]
- As [Datadog Logs][3]


Both methods are configured in `win32_event_log.d/conf.yaml` in the `conf.d/` folder at the root of the [Agent's configuration directory][4]. See the [sample win32_event_log.d/conf.yaml][3] for all available configuration options.


1. Edit the `wincrashdetect.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][2] to set `enabled: true`. See the [sample wincrashdetect.d/conf.yaml.example][3] for all available configuration options.

2. Enable the Windows Crash Detection module in `C:\ProgramData\Datadog\system-probe.yaml` by setting the enabled flag to 'true':

   ```yaml
    windows_crash_detection:
        enabled: true
    ```
3. [Restart the Agent][4].

### Validation

Check the information page in the Datadog Agent Manager or run the [Agent's `status` subcommand][6] and look for `winregistry` under the Checks section.

## Data Collected

### Metrics

All metrics collected by the Windows Registry integration are forwarded to Datadog.

### Logs

All logs collected by the Windows Registry integration are forwarded to Datadog, and subject to [Logs billing][7].

### Service Checks

The Windows Registry integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][8] with an [Agent Flare][9].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/metrics/#overview
[3]: https://docs.datadoghq.com/logs/
[4]:
[5]:
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/basic_agent_usage/windows/?tab=gui#agent-status-and-information
[7]: https://docs.datadoghq.com/account_management/billing/log_management/
[8]: https://docs.datadoghq.com/help/
[9]: https://docs.datadoghq.com/agent/troubleshooting/send_a_flare/?tab=agentv6v7
