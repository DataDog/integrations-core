# PowerShell Integration

## Overview

Collect custom metrics from read-only PowerShell `Get-*` cmdlets on Windows hosts. The integration maps cmdlet output properties to metrics and tags, allowing you to monitor Windows and application state that is exposed through PowerShell.

For security, the integration runs only cmdlets and parameters explicitly permitted in an administrator-owned allowlist.

**Minimum Agent version:** 7.84.0

## Setup

### Installation

The PowerShell integration is included in the [Datadog Agent][1] package. No additional installation is needed.

### Configuration

1. Edit `powershell_allowlist.yaml` to permit the read-only cmdlets and parameters that the Agent may run. The allowlist must be owned by Administrators or SYSTEM. The check fails closed if the file is missing, invalid, or owned by another user.

   The following example permits the check to query listening TCP connections and correlate them with running processes:

   ```yaml
   version: 1
   allowed_cmdlets:
     Get-NetTCPConnection:
       module: NetTCPIP
       parameters:
         State:
           required: false
           allowed_values:
             - Listen
     Get-Process:
       module: Microsoft.PowerShell.Management
   ```

   #### Allowlist options

   | Option | Type | Required | Description |
   | --- | --- | --- | --- |
   | `version` | integer | Yes | Allowlist schema version. The only supported value is `1`. |
   | `allowed_cmdlets` | mapping | Yes | Cmdlets that the check may run. The mapping must contain at least one entry, and each key must be a read-only cmdlet name in the form `Get-<Noun>`. |
   | `allowed_cmdlets.<cmdlet>.module` | string | Yes | Module that the cmdlet must resolve to at runtime. Use the value returned by `(Get-Command <cmdlet>).ModuleName`. Use `"*"` to explicitly skip module validation. |
   | `allowed_cmdlets.<cmdlet>.parameters` | mapping | No | Parameters that instances may pass to the cmdlet. Undeclared parameters are rejected. Parameter names may contain letters, numbers, and underscores. |
   | `allowed_cmdlets.<cmdlet>.parameters.<parameter>.required` | boolean | No; defaults to `false` | Whether every instance using the cmdlet must include this entry in `parameters`. |
   | `allowed_cmdlets.<cmdlet>.parameters.<parameter>.allowed_values` | list of strings | Conditional | Case-sensitive exact values permitted for the parameter. Boolean and numeric instance values are compared using their string forms. Every declared parameter must define `allowed_values` or `pattern`. If both are set, `allowed_values` is used for validation. |
   | `allowed_cmdlets.<cmdlet>.parameters.<parameter>.pattern` | string | Conditional | Case-sensitive Go RE2 expression defining permitted values. The expression is automatically anchored and must match the entire parameter value. RE2 does not support lookaround or backreferences. Every declared parameter must define `pattern` or `allowed_values`. |

   Unknown options cause the allowlist to be rejected. Cmdlet and parameter names are case-sensitive and must match the instance configuration. The allowlist constrains cmdlets and their `parameters`; `where` only removes output rows and does not need an allowlist entry. Cmdlets referenced by `tag_queries` must also appear in `allowed_cmdlets`. Tag queries invoke their target cmdlets without parameters, so those cmdlets cannot have any required allowlist parameters. Runtime module validation still applies.

2. Edit `powershell.d/conf.yaml` in the `conf.d` folder at the root of the Agent's [configuration directory][2]. See the [sample `powershell.d/conf.yaml`][3] for all available configuration options.

   The following example submits a constant custom metric for each listening TCP connection whose local address does not match `127.*`. It also runs `Get-Process` and joins `OwningProcess` from each connection to `Id` from each process to add a `process_name` tag:

   ```yaml
   instances:
     - cmdlet: Get-NetTCPConnection
       name: powershell
       parameters:
         - [State, Listen]
       where:
         - [LocalAddress, notlike, '127.*']
       tags:
         - connection_state:listen
       metrics:
         - [1, tcp_connection.info, gauge]
       tag_by:
         - LocalAddress AS local_address
         - LocalPort AS local_port
       tag_queries:
         - [OwningProcess, Get-Process, Id, ProcessName AS process_name]
   ```

   The equivalent PowerShell commands are:

   ```powershell
   Get-NetTCPConnection -State Listen |
     Where-Object -Property LocalAddress -NotLike -Value '127.*' |
     Select-Object LocalAddress, LocalPort, OwningProcess

   Get-Process |
     Select-Object Id, ProcessName
   ```

   The `parameters` option passes allowlisted named arguments directly to the cmdlet, while `where` filters the returned objects using PowerShell `Where-Object` semantics before selecting properties. All `where` entries must match for a row to be retained. The check then joins the results where `OwningProcess` equals `Id`.

   This configuration submits `powershell.tcp_connection.info`. A metric property may be a numeric property returned by the cmdlet or the literal `1` for a constant value. Non-numeric properties can be translated with the metric mapping form described in the sample configuration. Supported metric types are `gauge`, `rate`, `count`, `monotonic_count`, `histogram`, and `distribution`.

3. [Restart the Agent][4].

### Validation

[Run the Agent's status subcommand][5] and look for `powershell` under the **Checks** section.

## Data Collected

### Metrics

The PowerShell integration does not include default metrics. All metrics configured through this integration are forwarded to Datadog as [custom metrics][6], which may impact your billing.

### Events

The PowerShell integration does not include any events.

### Service Checks

The PowerShell integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][7] with an [Agent Flare][8].

[1]: /account/settings/agent/latest?platform=windows
[2]: https://docs.datadoghq.com/agent/configuration/agent-configuration-files/?tab=agentv6v7#agent-configuration-directory
[3]: https://github.com/DataDog/datadog-agent/blob/main/cmd/agent/dist/conf.d/powershell.d/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#restart-the-agent
[5]: https://docs.datadoghq.com/agent/basic_agent_usage/windows/?tab=gui#agent-status-and-information
[6]: https://docs.datadoghq.com/account_management/billing/custom_metrics/
[7]: https://docs.datadoghq.com/help/
[8]: https://docs.datadoghq.com/agent/troubleshooting/send_a_flare/?tab=agentv6v7
