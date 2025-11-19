## Overview

[Mac Audit Logs][1] captures detailed information about system events, user actions, network and security-related activities. These logs are crucial for monitoring system integrity, identifying unauthorized access, and ensuring adherence to security policies and regulations.

This integration provides enrichment and visualization for various log types, including:

- **Authentication and Authorization** events  
- **Administrative** activities  
- **Network** events  
- **File Access** activities  
- **Input/Output Control**  
- **IPC (Inter-Process Communication)**  

This integration collects Mac audit logs and sends them to Datadog for analysis, providing visual insights through out-of-the-box dashboards and the Log Explorer. It also helps monitor and respond to security threats with ready-to-use Cloud SIEM detection rules.

* [Log Explorer][2]
* [Cloud SIEM][3]

**Minimum Agent version:** 7.69.0

## Setup

### Installation

The Mac Audit Logs check is included in the [Datadog Agent][4] package, so you don't need to install anything else on your Mac.

### Configuration

#### Configure BSM Auditing on Mac
**Note**: The following steps are required for the Mac version >=14.

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

      ```yaml
      init_config:
      instances:
        - MONITOR: true
          AUDIT_LOGS_DIR_PATH: /var/audit
          min_collection_interval: 15
      logs:
        - type: integration
          service: mac-audit-logs
          source: mac-audit-logs
      ```

   **Note**:
     - Do not change the `service` and `source` values, as they are essential for proper log pipeline processing.
     - Default value for `AUDIT_LOGS_DIR_PATH` is `/var/audit`. In case of different BSM audit logging directory, please check `dir` value in `/etc/security/audit_control` file.

3. Give the user running `datadog-agent` access to the `/var/audit` directory.

4. Edit your `/etc/sudoers` file to give the user the ability to run these commands as `sudo`:

  ```shell
     <USER> ALL=(ALL) NOPASSWD:/usr/sbin/auditreduce
     <USER> ALL=(ALL) NOPASSWD:/usr/sbin/praudit
  ```

5. [Restart the Agent][7].

### Events

The Mac Audit Logs integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][8].


[1]: https://www.apple.com/mac/
[2]: https://docs.datadoghq.com/logs/explorer/
[3]: https://www.datadoghq.com/product/cloud-siem/
[4]: /account/settings/agent/latest
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/mac_audit_logs/datadog_checks/mac_audit_logs/data/conf.yaml.example
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[8]: https://docs.datadoghq.com/help/
