## Overview

* [Zeek][6] is the world's leading platform for network security monitoring. It interprets what it sees and creates compact, high-fidelity transaction logs, file content, and fully customized output, suitable for manual review on disk or in a more analyst-friendly tool like a security and information event management (SIEM) system.

This integration provides visualization and log enrichments for Connection Logs, DNS & DHCP Logs, Network Protocols, Files, Detections and Miscellaneous eventtypes.

#### Supported Logs:

- Opensource Zeek - JSON Format
  - **Event Types -** conn, dhcp, dns, ftp, http, ntp, rdp, smtp, snmp, socks, ssh, ssl, syslog, tunnel, files, pe, intel, notice, signatures, traceroute, known-certs, known-modbus, known-services, known-hosts, software, x509, dpd, weird, captureloss, reporter, ldap, ldap-search, smb-files, smb-mappings
- Corelight Zeek - Syslog RFC 3164 (Legacy) Format
  - **Event Types -** conn, dhcp, dns, ftp, http, ntp, rdp, smtp, snmp, socks, ssh, ssl, syslog, tunnel, files, pe, intel, notice, signatures, traceroute, known-certs, known-modbus, known-services, known-hosts, software, x509, dpd, weird, captureloss, reporter, ldap, ldap-search, smb-files, smb-mappings, conn-long, conn-red, encrypted-dns, generic-dns-tunnels, smtp-links, suricata-corelight

## Setup

### Installation

To install the Zeek integration follow the steps below:

**Note:** This step is not necessary for Agent version >= 7.18.0.

1. [Install][7] the 1.0 release (`zeek==1.0.0`)

**Opensource Zeek:**
1. [Install the Agent][4] on your Zeek machine.
2. Setup json-streaming-logs package
   - Install [Corelight Zeek plugin][5] for JSON logging
     ```
     /opt/zeek/bin/zkg install corelight/json-streaming-logs
     ```
   - Load ZKG packages
     ```
     echo -e "\n# Load ZKG packages\n@load packages" >> /opt/zeek/share/zeek/site/local.zeek
     ```
   - Restart the zeek
     ```
     /opt/zeek/bin/zeekctl install
     ```
     ```
     /opt/zeek/bin/zeekctl restart
     ```

**Corelight Zeek:**
* You have the [Datadog Agent][4] installed and running

### Configuration

#### Log collection

**Opensource Zeek:**
1. Collecting logs is disabled by default in the Datadog Agent. Enable it in datadog.yaml:
    ```
    logs_enabled: true
    ```

2. Add this configuration block to your zeek.d/conf.yaml file to start collecting your Zeek logs.
    ```
    logs:
    - type: file
        path: /opt/zeek/logs/current/*.log
        exclude_paths:
          - /opt/zeek/logs/current/*.*.log
        service: zeek
        source: zeek
    ```
**Note:** Ensure to include the log file's paths within the `exclude_paths` parameter to prevent the ingestion of unsupported or undesired log files during the monitoring process.
  
eg.
  ```
  exclude_paths:
    - /opt/zeek/logs/current/ntlm.log
    - /opt/zeek/logs/current/radius.log
    - /opt/zeek/logs/current/rfb.log
  ```

3. [Restart the Agent][1].

**Corelight Zeek:**
1. Collecting logs is disabled by default in the Datadog Agent. Enable it in datadog.yaml:
    ```
    logs_enabled: true
    ```

2. Add this configuration block to your zeek.d/conf.yaml file to start collecting your logs
    ```
    logs:
    - type: tcp
      port: <PORT>
      service: corelight
      source: zeek
    ```

3. [Restart the Agent][1].

4. Configuring Syslog Message Forwarding from corelight
    1. Access the Corelight Sensor UI:  
       - Open a web browser and navigate to the IP address or hostname of your Corelight sensor.
       - Log in with your administrative credentials.
    2. Navigate to the Zeek Configuration Page:  
       The exact path may vary depending on your sensor's firmware version. Look for options related to "Zeek" or "Logging".  
       Common paths include:  
        - Settings > Logging
        - Configuration > Zeek > Logging
    3. Enable Syslog Output:
        - Locate the option to enable syslog output for Zeek logs.
        - Select the checkbox or toggle to activate it.
    4. Specify Syslog Server Details:
       Provide the following information:
       - Syslog server IP address: The destination where you want to send the Zeek logs.
       - Syslog port: The port on which the syslog server is listening (typically 514).
       - Facility: The syslog facility to use.
       - Severity level: The minimum severity of events to send.
    5. Save and Apply Changes:  
       - Click the "Save" or "Apply" button to commit the configuration changes.


### Validation

[Run the Agent's status subcommand][2] and look for `zeek` under the Checks section.

## Data Collected

### Metrics

The zeek integration does not include any metrics.

### Events

The zeek integration does not include any events.

### Service Checks

The zeek integration does not include any service checks.

## Troubleshooting

**Opensource Zeek:**

If you see a **Permission denied** error while monitoring the log files, see the following instruction

   1. Give read permission to dd-agent user to monitor the log files
      ```
      sudo chown -R dd-agent:dd-agent /opt/zeek/current/
      ```
**Corelight Zeek:**

#### Permission denied while port binding:

If you see a **Permission denied** error while port binding in the Agent logs, see the following instructions:

   1. Binding to a port number under 1024 requires elevated permissions. Follow the instructions below to set this up.

      - Grant access to the port using the `setcap` command:

         ```
         sudo setcap CAP_NET_BIND_SERVICE=+ep /opt/datadog-agent/bin/agent/agent
         ```

      - Verify the setup is correct by running the `getcap` command:

         ```
         sudo getcap /opt/datadog-agent/bin/agent/agent
         ```

         With the expected output:

         ```
         /opt/datadog-agent/bin/agent/agent = cap_net_bind_service+ep
         ```

         **Note**: Re-run this `setcap` command every time you upgrade the Agent.

   2. [Restart the Agent][1].

#### Data is not being collected:

Make sure that traffic is bypassed from the configured port if the firewall is enabled.

#### Port already in use:

If you see the **Port <PORT-NO\> Already in Use** error, see the following instructions. The example below is for PORT-NO = 514:

On systems using Syslog, if the Agent listens for Zeek logs on port 514, the following error can appear in the Agent logs: `Can't start UDP forwarder on port 514: listen udp :514: bind: address already in use`.

This error occurs because by default, Syslog listens on port 514. To resolve this error, take **one** of the following steps:
- Disable Syslog
- Configure the Agent to listen on a different, available port

For any further assistance, do contact [Datadog support][3].

[1]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[3]: https://docs.datadoghq.com/help/
[4]: https://docs.datadoghq.com/agent/
[5]: https://github.com/corelight/json-streaming-logs
[6]: https://zeek.org/
[7]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install
