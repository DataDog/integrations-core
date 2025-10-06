# Agent Integration: Microsoft DNS

## Overview

[Microsoft DNS][4] is a Windows Server service that translates domain names into IP addresses, allowing computers to find and communicate with each other on a network. It supports features like Dynamic DNS (DDNS), zone transfers, conditional forwarding, DNSSEC for security, and scavenging to remove stale records.

This integration collects and enhances [DNS Server audit events][5], providing detailed insights through out-of-the-box dashboards. It also includes ready-to-use Cloud SIEM detection rules for improved monitoring and security.

**Minimum Agent version:** 7.68.0

## Setup

### Installation

To install the Microsoft DNS integration, run the following Agent installation command and the steps below. For more information, see the [Integration Management][6] documentation.

**Note**: This step is not necessary for Agent version >= 7.66.0.

Run powershell.exe as admin and execute following command:
  ```powershell
  & "$env:ProgramFiles\Datadog\Datadog Agent\bin\agent.exe" integration install datadog-microsoft_dns==1.0.0
  ```

### Configuration

#### Configure Log Collection

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in the `datadog.yaml` file with:

    ```yaml
      logs_enabled: true
    ```

2. Add this configuration block to your `microsoft_dns.d/conf.yaml` file to start collecting your Microsoft DNS Server audit events:

    ```yaml
      logs:
      - type: windows_event
        channel_path: "Microsoft-Windows-DNSServer/Audit"
        source: microsoft-dns
        service: microsoft-dns
        sourcecategory: windowsevent
    ```

3. [Restart the Agent][3].

### Validation

[Run the Agent's status subcommand][7] and look for `microsoft_dns` under the Checks section.

## Data Collected

### Logs

The Microsoft DNS integration collects the [DNS Server audit events][5].

### Metrics

The Microsoft DNS integration does not include any metrics.

### Events

The Microsoft DNS integration does not include any events.

### Service Checks

The Microsoft DNS integration does not include any service checks.

## Support

Need help? Contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/configuration/agent-commands/#restart-the-agent
[4]: https://learn.microsoft.com/en-us/windows-server/networking/dns/dns-overview
[5]: https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2012-r2-and-2012/dn800669(v=ws.11)#audit-events
[6]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=windowspowershell#install
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
