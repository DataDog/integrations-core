## Overview

[Mac Audit Logs][1] captures detailed information about system events, user actions, network and security-related activities. These logs are crucial for monitoring system integrity, identifying unauthorized access, and ensuring adherence to security policies and regulations.

This integration provides enrichment and visualization for various log types, including:

- **Authentication and Authorization** events  
- **Administrative** activities  
- **Network** events  
- **File Access** activities  
- **Input/Output Control**  
- **IPC (Inter-Process Communication)**  

This integration collects mac audit logs and sends them to Datadog for analysis, providing visual insights through out-of-the-box dashboards and Log Explorer. It also helps monitor and respond to security threats with ready-to-use Cloud SIEM detection rules.

* [Log Explorer][2]
* [Cloud SIEM][3]

## Setup

### Installation

To install the Mac Audit Logs integration, run the following Agent installation command and follow the steps below. For more information, see the [Integration Management][4] documentation.

**Note**: This step is not necessary for Agent versions >= 7.66.0

For Mac, run:
  ```shell
  sudo datadog-agent integration install datadog-mac-audit-logs==1.0.0
  ```


### Configuration

#### Configure BSM Auditing on Mac

1. Copy the configurations from `audit_control.example` to `audit_control`
    ```shell
    cp /etc/security/audit_control.example /etc/security/audit_control
    ```

2. Update the configuration to specify the event types that should be audited. Execute the command below to audit all event types:
    ```shell
    sudo sed -i '' 's/^flags:.*/flags:all/' /etc/security/audit_control && \
    sudo sed -i '' 's/^naflags:.*/naflags:all/' /etc/security/audit_control
    ```
3. Restart `auditd` service:
    ```shell
    /bin/launchctl enable system/com.apple.auditd
    ```

4. Restart the Mac.

**Note**: The above steps are needed for the mac version >=14.

### Validation

[Run the Agent's status subcommand][5] and look for `mac_audit_logs` under the Checks section.

## Data Collected

### Metrics

The Mac Audit Logs integration does not include any metrics.

### Log Collection

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in the `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Configure `mac_audit_logs.d/conf.yaml` file to start collecting Mac audit logs.

   See the [sample mac_audit_logs.d/conf.yaml][6] for available configuration options.

    * **Configuration for a Single MAC Machine**
      ```yaml
      init_config:
      instances:
        - MONITOR: true
          PORT: <PORT> 
          min_collection_interval: 15
      logs:
        - type: udp
          port: <PORT>
          service: mac-audit-logs
          source: mac-audit-logs
      ```

    * **Configuration for Centralized Monitoring**
      * Configuration on MAC device
        ```yaml
        init_config:
        instances:
          - MONITOR: true
            IP: <Centralized Machine IP>
            PORT: <PORT> 
            min_collection_interval: 15
        ```
      * Centralized Log Collection Configuration
        ```yaml
        logs:
            - type: udp
              port: <PORT>
              service: mac-audit-logs
              source: mac-audit-logs
        ```

   **Note**: 
     - Do not change the `service` and `source` values, as they are essential for proper log pipeline processing.
     - In case of Centralized monitoring, set `instances > IP` with the centralized device IP where the datadog agent is installed.
     - Ensure `instances > PORT` matches the value in `logs > port`.

3. [Restart the Agent][7].

#### Specify a time zone other than UTC in the Mac Audit Logs Datadog log pipeline

Datadog expects all logs to be in the UTC time zone by default. If the timezone of your Mac machine is not UTC, specify the correct time zone in the Mac Audit Logs Datadog pipeline.

To change the time zone in Mac Audit Logs pipeline:

  1. Navigate to the [**Pipelines** page][9] in the Datadog app. 

  2. Enter "Mac Audit Logs" in the  **Filter Pipelines** search box.

  3. Hover over the Mac Audit Logs pipeline and click on the **clone**  button. This will create an editable clone of the Mac Audit Logs pipeline.

  4. Edit the Grok Parser using the below steps:
      - In the cloned pipeline, find a processor with the name "Grok Parser: Parse \`record.time\` attribute" and click on the `Edit` button by hovering over the pipeline.
      - Under **Define parsing rules**,
        - Change the string `UTC` to the [TZ identifier][9] of the time zone of your MAC machine. For example, if your timezone is IST, you would change the value to`Asia/Calcutta`.
      - Click the **update** button.
### Events

The Mac Audit Logs integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][8].


[1]: https://www.apple.com/mac/
[2]: https://docs.datadoghq.com/logs/explorer/
[3]: https://www.datadoghq.com/product/cloud-siem/
[4]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/mac_audit_logs/datadog_checks/mac_audit_logs/data/conf.yaml.example
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[8]: https://docs.datadoghq.com/help/
[9]: https://app.datadoghq.com/logs/pipelines
