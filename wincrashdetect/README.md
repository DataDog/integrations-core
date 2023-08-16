# Windows Crash Detection Integration

## Overview

Get Datadog events upon Windows system crash to create monitors in Datadog.

**Note**: The list of metrics collected by this integration may change between minor Agent versions. Such changes may not be mentioned in the Agent's changelog.

## Setup

### Installation

The Windows Crash Detection integration is included in the [Datadog Agent][1] package, so you don't need to install anything else on your servers.

### Configuration

1. Edit the `wincrashdetect.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample wincrashdetect.d/conf.yaml.example][3] for all available configuration options.

2. Edit the `system-probe.yaml` folder at the root of your [Agent's configuration directory][2], to enable the system probe module.

2. [Restart the Agent][4].

### Validation

[Run the Agent's status subcommand][6] and look for `wincrashdetect` under the Checks section.

## Data Collected

### Metrics

No metrics are collected by this integration.

### Events

The Windows crash detection integration submits an event when a previously unreported crash is detected at agent startup.  The integration will report one event per crash.

### Service Checks

The Windows Kernel Memory integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][5].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/datadog-agent/blob/master/cmd/agent/dist/conf.d/wincrashdetect.d/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/help/
[6]: https://github.com/DataDog/integrations-core/blob/master/wincrashdetect/metadata.csv