## Overview

[Cisco Secure Firewall Threat Defense (FTD)][5] is a threat-focused, next-gen firewall (NGFW) with unified management. It provides advanced threat protection before, during, and after attacks.The [Cisco Secure Firewall Management Center (FMC)][7] is the centralized event and policy manager for Cisco Secure Firewall Threat Defense (FTD), both on-premises and virtual.

This integration enrich and ingests the following logs from Cisco Secure FTD using Cisco Secure FMC:
- User Authentication Logs
- SNMP Logs
- Failover Logs
- Transparent Firewall Logs
- Threat Detection Logs
- Security Events
- IP Stack Logs
- Application Firewall Logs
- Identity-based Firewall Logs
- Command Interface Logs
- OSPF Rotuing Logs
- RIP Routing Logs
- Resource Manager Logs
- VPN Failover Logs
- Intrusion Protection System Logs
- Dynamic Access Policies
- IP Address Assignment

Visualize detailed insights into SNMP requests, identity-based firewall logs, real time threat analysis, security detection and observation, and compliance monitoring with the out-of-the-box dashboards.

## Setup

### Installation

To install the Cisco Secure Firewall integration, run the following Agent installation command and the steps below. For more information, see the [Integration Management documentation][6].

**Note**: This step is not necessary for Agent version >= 7.52.0.

Linux command:
  ```shell
  sudo -u dd-agent -- datadog-agent integration install datadog-cisco_secure_firewall==1.0.0
  ```

### Configuration

#### Cisco Secure Firewall

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in `datadog.yaml`:
    ```yaml
    logs_enabled: true
    ```

2. Add this configuration block to your `cisco_secure_firewall.d/conf.yaml` file to start collecting your Cisco Secure Firewall logs.

    See the [sample cisco_secure_firewall.d/conf.yaml][6] for available configuration options.

      ```yaml
      logs:
       - type: tcp/udp
         port: <PORT>
         service: cisco-secure-firewall
         source: cisco-secure-firewall
      ```

3. [Restart the Agent][1].

4. Configure Syslog Message Forwarding from Cisco Secure Firewall Management Center:

    1. Select **Devices > Platform Settings** and create or edit an FTD policy.
    2. Select **Syslog > Logging Setup**.
       - **Enable Logging**: Turns on data plane system logging for the Firepower Threat Defense device.
       - **Enable Logging on the failover standby unit**: Turns on logging for the standby for the Firepower Threat Defense device, if available.
       - Click **Save**.
    3. Select **Syslog > Syslog Settings**.
       - Select **LOCAL7(20)** from Facility drop-down list.
       - Check the checkbox named **Enable Timestamp on Syslog Messages** to include the date and time a message was generated in the syslog message.
       - Select **RFC 5424 (yyyy-MM-ddTHH:mm:ssZ)** from the Timestamp Format dropdown list.
       - If you want to add a device identifier to syslog messages (which is placed at the beginning of the message), check the Enable Syslog Device ID check box and then select the type of ID.
          - **Interface**: To use the IP address of the selected interface, regardless of the interface through which the appliance sends the message. Select the security zone that identifies the interface. The zone must map to a single interface.
          - **User Defined ID**: To use a text string (up to 16 characters) of your choice.
          - **Host Name**: To use the hostname of the device.
       - Click **Save**.
    4. Select **Syslog > Syslog Server**.
       - Check the **Allow user traffic to pass when TCP syslog server is down** checkbox, to allow traffic if any syslog server that is using the TCP protocol is down.
       - Click **Add** to add a new syslog server.
          - In the **IP Address** dropdown menu, select a network host object that contains the IP address of the syslog server.
          - Choose the protocol (either TCP or UDP) and enter the port number for communications between the Firepower Threat Defense device and the syslog server.
          - Select Device Management Interface or Security Zones or Named Interfaces to communicate with the syslog server.
            - Security Zones or Named Interfaces: Select the interfaces from the list of Available Zones and click Add.
          - Click **OK**.
       - Click **Save**.
    5. Go to **Deploy > Deployment** and deploy the policy to assigned devices. The changes are not active until you deploy them.


### Validation

[Run the Agent's status subcommand][2] and look for `cisco_secure_firewall` under the Checks section.

## Data Collected

### Logs

The Cisco Secure Firewall integration collects user authentication, SNMP, failover, transparent firewall, IP stack, application firewall, identity based firewall, threat detection, command interface, security events, OSPF routing, RIP routing, resource manager, VPN failover, and intrusion protection system logs.

### Metrics

The Cisco Secure Firewall integration does not include any metrics.

### Events

The Cisco Secure Firewall integration does not include any events.

### Service Checks

The Cisco Secure Firewall integration does not include any service checks.

## Troubleshooting

### Cisco Secure Firewall

**Permission denied while port binding:**

If you see a **Permission denied** error while port binding in the Agent logs, see the following instructions:

   1. Binding to a port number under 1024 requires elevated permissions. Grant access to the port using the `setcap` command:

      - Grant access to the port using the `setcap` command:

         ```shell
         sudo setcap CAP_NET_BIND_SERVICE=+ep /opt/datadog-agent/bin/agent/agent
         ```

      - Verify the setup is correct by running the `getcap` command:

         ```shell
         sudo getcap /opt/datadog-agent/bin/agent/agent
         ```

         With the expected output:

         ```shell
         /opt/datadog-agent/bin/agent/agent = cap_net_bind_service+ep
         ```

         **Note**: Re-run this `setcap` command every time you upgrade the Agent.

   2. [Restart the Agent][1].

**Data is not being collected:**

Make sure that traffic is bypassed from the configured port if the firewall is enabled.

**Port already in use:**

If you see the **Port <PORT-NO\> Already in Use** error, see the following instructions. The example below is for PORT-NO = 514:

On systems using Syslog, if the Agent listens for Cisco Secure Firewall logs on port 514, the following error can appear in the Agent logs: `Can't start UDP forwarder on port 514: listen udp :514: bind: address already in use`.

This error occurs because by default, Syslog listens on port 514. To resolve this error, take **one** of the following steps:
- Disable Syslog.
- Configure the Agent to listen on a different, available port.

For any further assistance, contact [Datadog support][3].

[1]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[3]: https://docs.datadoghq.com/help/
[4]: https://docs.datadoghq.com/agent/
[5]: https://www.cisco.com/c/en/us/support/security/firepower-ngfw/series.html
[6]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install
[7]: https://www.cisco.com/c/en/us/products/collateral/security/firesight-management-center/datasheet-c78-736775.html