## Overview

[Cisco Secure Web Appliance][4] protects your organization by automatically blocking risky sites and testing unknown sites before allowing users access. It intercepts and monitors Internet traffic and applies policies to help keep your internal network secure from malware, sensitive data loss, productivity loss, and other Internet-based threats.


This integration ingests the following log types:
- Access Logs: This records all Web Proxy filtering and scanning activity.
- L4TM Logs: This records all Layer 4 Traffic Monitor activity.

Out-of-the-box (OOTB) dashboards help you to visualize detailed insights into Web Proxy filtering and scanning activity and Layer-4 Traffic Monitor activity. Additionally, (OOTB) detection rules are available to help you monitor and respond to potential security threats effectively.

**Disclaimer**: Use of this integration might collect data that includes personal information, is subject to your agreements with Datadog. Cisco is not responsible for the privacy, security, or integrity of any end-user information, including personal data, transmitted through your use of the integration.

**Minimum Agent version:** 7.65.0

## Setup

### Installation

To install the Cisco Secure Web Appliance integration, run the following Agent installation command and the steps below. For more information, see the [Integration Management][5] documentation.

**Note**: This step is not necessary for Agent version >= 7.58.0.

Linux command
  ```shell
  sudo -u dd-agent -- datadog-agent integration install datadog-cisco_secure_web_appliance==1.0.0
  ```

### Configuration
Access Logs can be collected either by port monitoring (when the retrieval method is Syslog Push) or by File Monitoring (when the retrieval method is SCP on Remote Server), depending on the chosen retrieval method.

L4TM Logs can only be collected by file monitoring using SCP on Remote Server as the retrieval method.
#### Logs Collection
**Tail File(File Monitoring)**

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in datadog.yaml:

    ```yaml
    logs_enabled: true
    ```

2. Add this configuration block to your cisco_secure_web_appliance.d/conf.yaml file to start collecting your Cisco Secure Web Appliance L4TM Logs.

    ```yaml
      logs:
      - type: file
        path: <Path to Directory Where Logs would Get Stored>
        service: l4tm_logs
        source: cisco-secure-web-appliance
    ```

3. If the chosen retrieval method for Access Logs is SCP on Remote Server, add the configuration block for Access Logs in the above configuration to start collecting your Cisco Secure Web Appliance Access Logs along with L4TM Logs. The configuration will appear as follows in cisco_secure_web_appliance.d/conf.yaml.
    
    ```yaml
      logs:
      - type: file
        path: <Path to Directory Where L4TM Logs would Get Stored>
        service: l4tm_logs
        source: cisco-secure-web-appliance
      - type: file
        path: <Path to Directory Where Access Logs would Get Stored>
        service: access_logs
        source: cisco-secure-web-appliance
    ```
    **NOTE**: Please make sure that `path` value is similar to the Directory configured in the `Configure SCP on Remote Server for L4TM Logs` and `Configure SCP on Remote Server for Access Logs` sections respectively, forwarding /*.s

4. [Restart the Agent][3].

**Syslog**

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in datadog.yaml:

    ```yaml
    logs_enabled: true
    ```
2. If the chosen retrieval method for Access Logs is Syslog Push, add the configuration block for Access Logs in the configuration file to start collecting your Cisco Secure Web Appliance Access Logs along with L4TM Logs. The configuration will appear as follows in cisco_secure_web_appliance.d/conf.yaml.

    We will be using the UDP method to collect the Cisco Secure Web Appliance Access Logs.
    See the sample [cisco_secure_web_appliance.d/conf.yaml][7] for available configuration options.

    ```yaml
      logs:
      - type: file
        path: <Path to Directory Where L4TM Logs would Get Stored>
        service: l4tm_logs
        source: cisco-secure-web-appliance
      logs:
      - type: udp
        port: <PORT>
        service: access_logs
        source: cisco-secure-web-appliance
    ```
    **Note**: It is important not to change the service and source values, as these parameters are integral to the pipeline's operation.
    
3. [Restart the Agent][3].

### Configuration on Cisco Secure Web Appliance portal

#### Steps to set time zone to GMT
Datadog expects that all logs are in the GMT time zone by default. Please ensure that the time zone configured in your Cisco Secure Web Appliance portal is GMT. Here are the steps to change the time zone:
1. Go to **System Administration**, and then **Time Zone**.
2. Click on **Edit Settings**.
3. Select **GMT Offset** as the region.
4. Select **GMT** as the country.
5. Select **GMT (GMT)** as the time zone.
6. Submit and commit the changes.

#### Configure Log Subscriptions

#### Configure Syslog Push for Access Logs:

**Prerequisites:**
- The datadog-agent server hostname where you want to push the logs.

**Configuration:**

1. Log in to the Cisco Secure Web Appliance UI.
2. Navigate to  **System Administration** > **Log Subscriptions**.
3. In order to add an Access Logs subscription, click **Add Log Subscription**.
4. Select **Log Type** as **Access Logs**.
5. Provide a Log Name.
6. Choose the **Squid** option for **Log Style**.
    **Note**: The default (squid) log style for access logs is supported. 
7. Select the **Syslog Push** option as the **Retrieval Method**.
8. Provide the following details.

    Hostname: \<Datadog-Agent Host Server>

    Port: \<Default Provided>

    Protocol: UDP
    
    Maximum message size: \<Valid values for UDP are 1024 to 9216>
    
    Facility: \<Default Selected>
9. Click **Submit**. 
10. Click **Commit Changes** at the top right of the **Log Subscriptions** page.
    **Note:** These changes will not go into effect until they are committed.

#### Configure SCP on Remote Server for L4TM Logs

**Prerequisites:**
- Requires the hostname and username (admin account username is not necessary) of VM/machine where the Datadog Agent is installed.

**Configuration:**
1. Navigate to  **System Administration** > **Log Subscriptions** in the Cisco Secure Web Appliance UI.
2. To add a log subscription for Traffic Monitor Logs, click **Add Log Subscription**.  
3. Select **Traffic Monitor Logs** as **Log Type**.
4. Provide the appropriate log name.
5. For **FileName**, provide a new name or keep the default name.
6. Choose **SCP on Remote Server** as **Retrieval Method**.
7. Provide the following information.

    SCP Host: \<SCP Host IP Address>

    Directory: \<Path to Directory Where Logs would Get Stored>
    **NOTE:** Make sure that Directory does not have any other log files.

    SCP Port: \<Default Port>

    Username: \<SCP Host Username>
8. Click **Submit**. After submitting, SSH key(s) are generated. Copy and save the SSH key(s) as it is only visible once.
9. Place the SSH key(s) into your `authorized_keys` file on the remote host so that the log files can be uploaded.
10. Click **Commit Changes** at top right of **Log Subscriptions** page.

    **NOTE:** These changes will not go into effect until you commit them.

#### Configure SCP on Remote Server for Access Logs.

**Prerequisites:**
- Requires the hostname and username (admin account username is not necessary) of VM/machine where the Datadog Agent is installed.

**Configuration:**
1. In the Cisco Secure Web Appliance UI, go to **System Administration** > **Log Subscriptions**.
2. To add a new log subscription for Access Logs, click **Add Log Subscription** or edit an existing Access Logs Subscription.
3. If you are adding a new subscription, then follow steps 4 to 6 mentioned in the Configure Syslog Push for Access Logs section or this topic.
4. If you are editing an existing Access Logs Subscription, select **SCP on the Remote Server** as the **Retrieval Method**.
5. Provide the following information:

    SCP Host: \<SCP Hostname>

    SCP Port: \<Default Provided>
    
    Directory: \<Path to store the Log Files>
    **Note:** Make sure that Directory does not have any other log files.
    
    Username: \<SCP Server Username>
6. Click **Submit**. Once you click **Submit**,  SSH key(s) are generated. Copy the SSH Key and save it somewhere as it is only displayed once. 
7. Place the SSH key(s) into your `authorized_keys` file on the remote host so log files can be uploaded.
8. Click **Commit Changes** at top right of the **Log Subscriptions** page.
    **Note:** These changes do not go into effect until you commit them.


For more information on configuration, visit the [Cisco Secure Web Appliance official documentation][8].

### Validation

[Run the Agent's status subcommand][6] and look for `cisco_secure_web_appliance` under the Checks section.

## Data Collected

### Log 

| Format     | Event Types    |
| ---------  | -------------- |
| syslog | access_logs, l4tm_logs |

### Metrics

The Cisco Secure Web Appliance does not include any metrics.

### Events

The Cisco Secure Web Appliance integration does not include any events.

### Service Checks

The Cisco Secure Web Appliance integration does not include any service checks.

## Troubleshooting

**Permission denied while port binding:**

If you see a **Permission denied** error while port binding in the Agent logs, see the following instructions:

1. Binding to a port number under 1024 requires elevated permissions. Grant access to the port using the `setcap` command:
    ```shell
    sudo setcap CAP_NET_BIND_SERVICE=+ep /opt/datadog-agent/bin/agent/agent
    ```

2. Verify the setup is correct by running the `getcap` command:

    ```shell
    sudo getcap /opt/datadog-agent/bin/agent/agent
    ```

    With the expected output:

    ```shell
    /opt/datadog-agent/bin/agent/agent = cap_net_bind_service+ep
    ```

    **Note**: Re-run this `setcap` command every time you upgrade the Agent.
3. [Restart the Agent][3].


**Permission denied while file monitoring:**

If you see a **Permission denied** error while monitoring the log files, give the `dd-agent` user read permission on them.
  ```shell
    sudo chmod g+s Path/to/Directory/Where/Logs/would/Get/Stored/
  ```
  ```shell
    sudo chgrp dd-agent Path/to/Directory/Where/Logs/would/Get/Stored/
  ```


**Data is not being collected:**

Ensure that traffic is bypassed from the configured port if the firewall is enabled.

**Port already in use:**

If you see the **Port \<PORT-NO> Already in Use** error, see the following instructions. The example below is for PORT-NO = 514:
On systems using Syslog, if the Agent listens for access_logs logs on port 514, the following error can appear in the Agent logs: `Can't start UDP forwarder on port 514: listen udp :514: bind: address already in use`.
This error occurs because by default, Syslog listens on port 514. To resolve this error, take **one** of the following steps: 
    - Disable Syslog 
    - Configure the Agent to listen on a different, available port


For any further assistance, contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: /account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[4]: https://www.cisco.com/site/in/en/products/security/secure-web-appliance/index.html
[5]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/cisco_secure_web_appliance/datadog_checks/cisco_secure_web_appliance/data/conf.yaml.example
[8]: https://www.cisco.com/c/en/us/td/docs/security/wsa/wsa-14-5/user-guide/wsa-userguide-14-5/b_WSA_UserGuide_11_7_chapter_010101.html#task_1686002
