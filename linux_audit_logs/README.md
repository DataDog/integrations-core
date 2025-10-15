## Overview

[Linux Audit Logs][3] record detailed information about system events, user activities, and security-related actions. They are essential for monitoring system integrity, detecting unauthorized access, and ensuring compliance with security policies and regulations.

This integration provides enrichment and visualization for various log types, including:
- **Mandatory Access Control (MAC)** configurations and status  
- **MAC policies**
- **Role** assignments, removals, and user role changes  
- **Audit** configuration changes and audit daemon events (such as aborts, configuration changes)  
- **User authentication** events  
- **User account** credential modifications  
- **User and group** management activities  
- **SELinux user** errors  
- **Access Vector Cache (AVC)** logs  

It supports these logs across **Red Hat**, **Ubuntu**, and **CentOS** Linux operating systems.

This integration collects Linux audit logs and sends them to Datadog for analysis. It provides visual insights through out-of-the-box dashboards and the Log Explorer, and helps monitor and respond to security threats using ready-to-use Cloud SIEM detection rules.

* [Log Explorer][4]
* [Cloud SIEM][5]

**Minimum Agent version:** 7.67.0

## Setup

### Installation

To install the Linux Audit Logs integration, run the following Agent installation command. For more information, see [Integration Management][6].

**Note**: This step is not necessary for Agent versions >= 7.66.0

For Linux, run:
  ```shell
  sudo -u dd-agent -- datadog-agent integration install datadog-linux-audit-logs==1.0.0
  ```

### Configuration

#### Install the Audit Daemon (`auditd`) 

1. Install `auditd` on Linux:
    - **Debian/Ubuntu:**

      ```shell
      sudo apt-get update
      sudo apt-get install auditd
      ```

    - **CentOS/RHEL:**

      ```shell
      sudo yum install audit
      ```

2. Start the Audit Daemon:

    ```shell
    sudo systemctl start auditd
    ```

3. Enable the Audit Daemon to Start on Boot:
    ```shell
    sudo systemctl enable auditd
    ```

4. Verify the Status of the Audit Daemon:
    ```shell
    sudo systemctl status auditd
    ```

#### Configure the Audit Daemon (`auditd`)

1. Give the `dd-agent` user read permission for rotated audit log files:
    ```shell
    sudo grep -q "^log_group=" /etc/audit/auditd.conf && sudo sed -i 's/^log_group=.*/log_group=dd-agent/' /etc/audit/auditd.conf || echo "log_group = dd-agent" | sudo tee -a /etc/audit/auditd.conf
    ```

2. Restart Audit Daemon:
    ```shell
    sudo systemctl restart auditd
    ```

### Validation

[Run the Agent's status subcommand][8] and look for `linux_audit_logs` under the Checks section.

## Data Collected

### Metrics

The Linux Audit Logs integration does not include any metrics.

### Log Collection

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in the `datadog.yaml` file:

   ```yaml
   logs_enabled: true
   ```

2. Give the `dd-agent` user read access to the `audit.log` file:

    ```shell
    sudo chown -R dd-agent:dd-agent /var/log/audit/audit.log
    ```

3. Add this configuration block to your `linux_audit_logs.d/conf.yaml` file to start collecting Linux audit logs.

   See the [sample linux_audit_logs.d/conf.yaml][7] for available configuration options.

   ```yaml
   logs:
     - type: file
       path: /var/log/audit/audit.log
       service: linux-audit-logs
       source: linux-audit-logs
   ```
   **Note**: Do not change the `service` and `source` values, as they are essential for proper log pipeline processing.

4. [Restart the Agent][2].

### Events

The Linux Audit Logs integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[3]: https://linux.org/
[4]: https://docs.datadoghq.com/logs/explorer/
[5]: https://www.datadoghq.com/product/cloud-siem/
[6]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install
[7]: https://github.com/DataDog/integrations-core/blob/master/linux_audit_logs/datadog_checks/linux_audit_logs/data/conf.yaml.example
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
