# Agent Integration: Microsoft Sysmon

## Overview

[Microsoft Sysmon][4] is a Windows system service and device driver that provides detailed logging of system activity, including process creation, network connections, file modifications, and registry changes.

This integration enriches and ingests the [Sysmon event logs][5]. Use pre-built dashboard to get a high-level view of Sysmon events helping security teams monitor system activity.

## Setup

### Installation

To install the Microsoft Sysmon integration, run the following Agent installation command and the steps below. For more information, see the [Integration Management][6] documentation.

**Note**: This step is not necessary for Agent version >= 7.66.0.

Run powershell.exe as admin and execute following command:
  ```powershell
  & "$env:ProgramFiles\Datadog\Datadog Agent\bin\agent.exe" integration install datadog-microsoft_sysmon==1.0.0
  ```

### Configuration

#### Configure Log Collection

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in the `datadog.yaml` file with:

    ```yaml
      logs_enabled: true
    ```

2. Add this configuration block to your `microsoft_sysmon.d/conf.yaml` file to start collecting your Microsoft Sysmon logs:

    ```yaml
      logs:
      - type: windows_event
        channel_path: "Microsoft-Windows-Sysmon/Operational"
        source: microsoft-sysmon
        service: microsoft-sysmon
        sourcecategory: windowsevent
    ```

3. [Restart the Agent][3].

#### Configure Sysmon

Follow these steps to install Sysmon:
1. Download the zip file from the [Sysmon download page][4]. Extract its zip file content.
2. Create an XML file for configuring Sysmon. For example, if you want to monitor processes created by apps from AppData folders, the configuration file will look like content shown below, you can add more event filters under the `EventFiltering` XML tag for other events in the same way.

  ```xml
    <Sysmon schemaversion="4.90">
        <EventFiltering>
          <ProcessCreate onmatch="include">
              <Image condition="contains">C:\Users\*\AppData\Local\Temp\</Image>
              <Image condition="contains">C:\Users\*\AppData\Roaming\</Image>
          </ProcessCreate>
        </EventFiltering>
    </Sysmon>
  ```

3. Execute the command as admin from the extracted folder:

  ```powershell
    .\Sysmon -i [<configfile>]
  ```

**Note:** Sysmon is highly configurable using the configuration (XML) file which allows you to:
- Control which events to monitor
- Filter events based on processes, paths, etc.

Enabling too many event types can result in excessive data ingestion. Only critical security events should be enabled based on threat model and monitoring needs.
These events should be selectively enabled for critical system directories, processes, and users to avoid unnecessary log noise.

For more details on configuration, please refer to the [Sysmon docs][7].

### Validation

[Run the Agent's status subcommand][8] and look for `microsoft_sysmon` under the Checks section.

## Data Collected

### Logs

The Microsoft Sysmon integration collects the following [Sysmon event logs][5]:
- Process activity logs
- Network activity logs
- File activity logs
- Registry activity logs
- WMI activity logs
- Sysmon service activity logs
- Named Pipe and Clipboard activity logs

### Metrics

The Microsoft Sysmon integration does not include any metrics.

### Events

The Microsoft Sysmon integration does not include any events.

### Service Checks

The Microsoft Sysmon integration does not include any service checks.

## Support

Need help? Contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/configuration/agent-commands/#restart-the-agent
[4]: https://learn.microsoft.com/en-us/sysinternals/downloads/sysmon
[5]: https://learn.microsoft.com/en-us/sysinternals/downloads/sysmon#events
[6]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=windowspowershell#install
[7]: https://learn.microsoft.com/en-us/sysinternals/downloads/sysmon#configuration-files
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
