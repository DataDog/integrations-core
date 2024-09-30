## Overview

[Cisco Secure Web Appliance][4] protects your organization by automatically blocking risky sites and testing unknown sites before allowing users access. It intercepts and monitors Internet traffic and applies policies to help keep your internal network secure from malware, sensitive data loss, productivity loss, and other Internet-based threats.


This integration ingests the following types of logs:
- Access Logs: This records all Web Proxy filtering and scanning activity.
- L4TM Logs: This records all Layer-4 Traffic Monitor activity.

Visualize detailed insights into Web Proxy filtering and scanning activity and Layer-4 Traffic Monitor activity through the out-of-the-box dashboards.Additionally, out-of-the-box detection rules are available to help you monitor and respond to potential security threats effectively.

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


#### Steps to configure Syslog Push for Access Logs:

**Prerequisites:**
1. Require Syslog server hostname(Your Datadog Agent Server) where you want to push the logs.

**Configuration:**

1. Login to Cisco Secure Web Appliance UI.
2. Navigate to  System Administration -> Log Subscriptions.
3. In order to add  Access Logs subscription, click on the Add 'Log Subscription…' button.
4. Select Log Type as Access Logs.
5. Provide Log Name.
6. Choose ‘Squid’ Option for Log Style.\
    **Note**: We will support default (squid) log style for access log. 
7. Select ‘Syslog Push’ Option as Retrieval Method.
8. Provide Following Details.

    Hostname: \<Datadog-Agent Host Server>

    Port: \<Default Provided>

    Protocol: UDP
    
    Maximum message size: \<Valid values for UDP are 1024 to 9216>
    
    Facility: \<Default Selected>
9. Click on Submit. 
10. Click on Commit Changes at top right-side of Log Subscriptions Page.
    NOTE: These changes will not go into effect until you commit them.

#### Steps to configure SCP on Remote Server for L4TM Logs.

**Prerequisites:**
1. Requires SCP Host and Username for the same.

**Configuration:**
1. Navigate to  System Administration -> Log Subscriptions in Cisco Secure Web Appliance UI.
2. To add a log subscription for Traffic Monitor Logs, click on  Add 'Log Subscription…'  
3. Select Traffic Monitor Logs as Log Type.
4. Provide appropriate Log Name.
5. For FileName, provide a new name or keep the default added name.
6. Choose SCP on Remote Server as Retrieval Method.
7. Provide Following Information.

    SCP Host: \<SCP Host IP Address>

    Directory: \<Path to Directory Where Logs would Get Stored>
    
    **NOTE:** Make sure that Directory does not have any other log files.
    SCP Port: \<Default Port>
    Username: \<SCP Host Username>
8. Click on Submit. After submitting, SSH key(s)  will get generated. Copy and save both the SSH key(s) as it is only visible once.
9. Place the given SSH key(s) into your ‘authorized_keys’ file on the remote host so that the log files can be uploaded.
10. Click on Commit Changes at top right-side of Log Subscriptions Page.

    **NOTE:** These changes will not go into effect until you commit them.

#### Steps to configure SCP on Remote Server for Access Logs.

**Prerequisites:**
1. Requires SCP Host and Username for the same.

**Configuration:**
1. Go to System Administration -> Log Subscriptions in Cisco Secure Web Appliance UI.
2. To add a new log subscription for Access Logs, click Add 'Log Subscription…'  OR edit already configured Access Logs Subscription.
3. If you are adding a new subscription then follow the steps 4 to 6 mentioned in the configuration of Syslog Push for Access Logs.
4. If you are editing existing Access Logs Subscription, select SCP on Remote Server as Retrieval Method.
5. Provide following information:

    SCP Host: \<SCP Hostname>

    SCP Port: \<Default Provided>
    
    Directory: \<Path to store the Log Files>
    
    **NOTE:** Make sure that Directory does not have any other log files.
10. Username: \<SCP Server Username>
11. Click on Submit. Once you click on ‘Submit’,  SSH key(s) will get generated. Copy the SSH Key and save it somewhere as this will be only displayed once. 
12. Place the given SSH key(s) into your ‘authorized_keys’ file on the remote host so that the log files can be uploaded.
Click on Commit Changes at top right-side of Log Subscriptions Page.

    **NOTE:** These changes will not go into effect until you commit them.

#### Steps to set time zone to GMT in Cisco Secure Web Appliance 

Since Datadog expects all the logs in GMT timezone by default, if the time zone of your Cisco Secure Web Appliance logs is other than GMT, please change it to GMT. Here are the steps:
1. Go to System Administration->Time Zone.
2. Click on 'Edit Settings...'.
3. Select GMT Offset as the region.
4. Select GMT as the Country.
5. Select GMT (GMT) as the time zone.
6. Submit and commit the changes.



### Validation

[Run the Agent's status subcommand][6] and look for `cisco-secure-web-appliance` under the Checks section.

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

Make sure that traffic is bypassed from the configured port if the firewall is enabled.

**Port already in use:**

- If you see the **Port \<PORT-NO> Already in Use** error, see the following instructions. The example below is for PORT-NO = 514:

- On systems using Syslog, if the Agent listens for access_logs logs on port 514, the following error can appear in the Agent logs: `Can't start UDP forwarder on port 514: listen udp :514: bind: address already in use`.

- This error occurs because by default, Syslog listens on port 514. To resolve this error, take **one** of the following steps: 

    - Disable Syslog 
    - Configure the Agent to listen on a different, available port


For any further assistance, contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[4]: https://www.cisco.com/site/in/en/products/security/secure-web-appliance/index.html
[5]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/cisco_secure_web_appliance/datadog_checks/cisco_secure_web_appliance/data/conf.yaml.example