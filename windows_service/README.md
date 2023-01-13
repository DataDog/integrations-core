# Agent Check: Windows Service

## Overview

This check monitors the state of any Windows Service and submits a service check to Datadog.

## Setup

### Installation

The Windows Service check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Windows hosts.

### Configuration

The configuration is located in the `windows_service.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample windows_service.d/conf.yaml][3] for all available configuration options. When you are done editing the configuration file [Restart the Agent][4] to load the new configuration.

The check can monitor all services on the system or selectively monitor a few services by name. Beginning with Agent version 7.41 the check can select which services to monitor based on their startup type.

This example configuration monitors only the `Dnscache` and `wmiApSrv` services:
```yaml
instances:
  - services:
    - dnscache
    - wmiapsrv
```

This examples uses the `ALL` keyword to monitor all services. If any of the service names are set to `ALL` then the other patterns in the instance will be ignored.
```yaml
instances:
  - services:
    - ALL
```

The check uses case-insensitive [Python regular expressions][11] when matching the service names. If a service name includes special characters you must escape the special characters with a `\`. For example, `MSSQL$CRMAWS` becomes  `MSSQL\$CRMAWS` and `Web Server (prod)` becomes `Web Server \(prod\)`. The service name pattern will match all service names that start with the pattern, for an exact match use the regular expression `^service$`.

Provide service names as they appear in the service name field, **NOT** the display name field. For example, configure the service name `datadogagent` **NOT** the display name `Datadog Agent`.

<p align="center">
<img alt="Datadog Agent service properties" src="https://raw.githubusercontent.com/DataDog/integrations-core/master/windows_service/images/service-properties.png"/>
</p>

Beginning with Agent version 7.41 the check can select which services to monitor based on their startup type.
For example, to monitor only the services that have an `automatic` or `automatic_delayed_start` startup type.
```yaml
instances:
  - services:
    - startup_type: automatic
    - startup_type: automatic_delayed_start
```
The possible values for `startup_type` are:
- disabled
- manual
- automatic
- automatic_delayed_start

#### Tags

The check automatically tags the Windows service name to each service check in the `windows_service:<SERVICE>` tag. The `<SERVICE>` name in the tag will be lowercased and have special characters replaced, see [Getting Started with Tags][12] for more information.

**NOTE:** The check also automaticlly tags the Windows service name to each service check in the `service:<SERVICE>` tag. **This behavior is deprecated** and the check will stop automatically assigning this tag in a future version of the agent. To stop the check from automatically assigning this tag and to disable the associated deprecation warning set the `disable_legacy_service_tag` option. See [Assigning Tags][13] for information on how to assign the `service` tag to a service.

Beginning with Agent version 7.40 the check can add a `windows_service_startup_type:<STARTUP_TYPE>` tag to each service check to indicate the startup type of the service. Set the `windows_service_startup_type_tag` option to include this tag with each service check.

### Validation

[Run the Agent's status subcommand][5] and look for `windows_service` under the Checks section.

## Data Collected

### Metrics

The Windows Service check does not include any metrics.

### Events

The Windows Service check does not include any events.

### Service Checks

See [service_checks.json][6] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][7].

## Further Reading

- [Monitoring Windows Server 2012][8]
- [How to collect Windows Server 2012 metrics][9]
- [Monitoring Windows Server 2012 with Datadog][10]

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[3]: https://github.com/DataDog/integrations-core/blob/master/windows_service/datadog_checks/windows_service/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/windows_service/assets/service_checks.json
[7]: https://docs.datadoghq.com/help/
[8]: https://www.datadoghq.com/blog/monitoring-windows-server-2012
[9]: https://www.datadoghq.com/blog/collect-windows-server-2012-metrics
[10]: https://www.datadoghq.com/blog/windows-server-monitoring
[11]: https://docs.python.org/3/howto/regex.html#regex-howto
[12]: https://docs.datadoghq.com/getting_started/tagging/
[13]: https://docs.datadoghq.com/getting_started/tagging/assigning_tags/
