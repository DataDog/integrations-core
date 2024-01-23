# Agent Check: Windows Service

## Overview

This check monitors the state of any Windows Service and submits a service check to Datadog.

## Setup

### Installation

The Windows Service check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Windows hosts.

### Configuration

The configuration is located in the `windows_service.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][2]. See the [sample windows_service.d/conf.yaml][3] for all available configuration options. When you are done editing the configuration file, [restart the Agent][4] to load the new configuration.

The check can monitor all services on the system or selectively monitor a few services by name. Beginning with Agent version 7.41, the check can select which services to monitor based on their startup type.

This example configuration monitors only the `Dnscache` and `wmiApSrv` services:
```yaml
instances:
  - services:
    - dnscache
    - wmiapsrv
```

This example uses the `ALL` keyword to monitor all services on the host. If the `ALL` keyword is used, the other patterns in the instance are ignored.
```yaml
instances:
  - services:
    - ALL
```

The check uses case-insensitive [Python regular expressions][11] when matching service names. If a service name includes special characters, you must escape the special characters with a `\`. For example, `MSSQL$CRMAWS` becomes  `MSSQL\$CRMAWS` and `Web Server (prod)` becomes `Web Server \(prod\)`. The service name pattern matches all service names that start with the pattern. For an exact match, use the regular expression `^service$`.

Provide service names as they appear in the service name field, **NOT** the display name field. For example, configure the service name `datadogagent` **NOT** the display name `Datadog Agent`.

<p align="center">
<img alt="Datadog Agent service properties" src="https://raw.githubusercontent.com/DataDog/integrations-core/master/windows_service/images/service-properties.png"/>
</p>

Beginning with Agent version 7.41, the check can select which services to monitor based on their startup type.
For example, to monitor only the services that have an `automatic` or `automatic_delayed_start` startup type.
```yaml
instances:
  - services:
    - startup_type: automatic
    - startup_type: automatic_delayed_start
```

The possible values for `startup_type` are:
- `disabled`
- `manual`
- `automatic`
- `automatic_delayed_start`

Beginning with Agent version 7.50, the check can select which services to monitor based on whether they have a [Service Trigger assigned][17].
Below are some examples showing possible configurations.
```yaml
# Matches all services that do not have a trigger
services:
  - trigger_start: false

# Matches all services with an automatic startup type and excludes services with triggers
services:
  - startup_type: automatic
    trigger_start: false

# Only matches EventLog service when its startup type is automatic and has triggers
services:
  - name: EventLog
    startup_type: automatic
    trigger_start: true
```

#### Tags

The check automatically tags the Windows service name to each service check in the `windows_service:<SERVICE>` tag. The `<SERVICE>` name in the tag uses lowercase and special characters are replaced with underscores. See [Getting Started with Tags][12] for more information.

**NOTE:** The check also automatically tags the Windows service name to each service check in the `service:<SERVICE>` tag. **This behavior is deprecated**. In a future version of the Agent, the check will stop automatically assigning this tag. To stop the check from automatically assigning this tag and to disable the associated deprecation warning, set the `disable_legacy_service_tag` option. See [Assigning Tags][13] for information on how to assign the `service` tag to a service.

Beginning with Agent version 7.40, the check can add a `windows_service_startup_type:<STARTUP_TYPE>` tag to each service check to indicate the startup type of the service. Set the `windows_service_startup_type_tag` option to include this tag with each service check.

### Validation

[Run the Agent's status subcommand][5] and look for `windows_service` under the **Checks** section.

## Data Collected

### Metrics

The Windows Service check does not include any metrics.

### Events

The Windows Service check does not include any events.

### Service Checks

See [service_checks.json][6] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][7].

### Service permissions
If a service is present and matches the configuration, but the Datadog Agent does not report a service check for the service, the Datadog Agent might have insufficient permissions. For example, by default the Datadog Agent does not have access to the NTDS Active Directory Domain Services service. To verify this, run the check from an **elevated (run as Admin)** PowerShell shell.

```powershell
& "$env:ProgramFiles\Datadog\Datadog Agent\bin\agent.exe" check windows_service
```
If the service is present in the output, permissions are the issue. To give the Datadog Agent permission [grant `Read` access on the service][14] to the [Datadog Agent User][15]. We recommend [granting `Read` access with Group Policy][16] to ensure the permissions persist through Windows Updates.

## Further Reading

- [Monitoring Windows Server 2012][8]
- [How to collect Windows Server 2012 metrics][9]
- [Monitoring Windows Server 2012 with Datadog][10]

[1]: https://app.datadoghq.com/account/settings/agent/latest
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
[14]: https://learn.microsoft.com/en-us/troubleshoot/windows-server/windows-security/grant-users-rights-manage-services
[15]: https://docs.datadoghq.com/agent/guide/windows-agent-ddagent-user/
[16]: https://learn.microsoft.com/en-US/troubleshoot/windows-server/group-policy/configure-group-policies-set-security
[17]: https://learn.microsoft.com/en-us/windows/win32/services/service-trigger-events
