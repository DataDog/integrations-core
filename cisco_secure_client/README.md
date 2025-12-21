## Overview

[Cisco Secure Client][4] (formerly AnyConnect) provides secure, encrypted VPN access for users connecting to internal resources. It ensures reliable remote connectivity, and handles sessions, licensing, and client version compatibility to maintain consistent security across multiple devices.

Integrate Cisco Secure Client with Datadog to gain insights into VPN client behavior, connection status, and authentication events using pre-built dashboard visualizations. Datadog uses its built-in log pipelines to parse and enrich these logs, facilitating easy search and detailed insights. The integration can also be used for Cloud SIEM detection rules for enhanced monitoring and security.

**Minimum Agent version:** 7.74.0

**Disclaimer**: Your use of this integration, which may collect data that includes personal information, is subject to your agreements with Datadog. Cisco is not responsible for the privacy, security or integrity of any end-user information, including personal data, transmitted through your use of the integration.

## Setup

### Configuration

#### Log collection

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in `datadog.yaml`:
/root/Bitbucket/datadog-security-connectors
    ```yaml
    logs_enabled: true
    ```

2. Add this configuration block to your `cisco_secure_client.d/conf.yaml` file to start collecting your Cisco Secure Client logs.

      ```yaml
      logs:
        - type: tcp/udp
          port: <PORT>
          service: cisco-secure-client
          source: cisco-secure-client
          log_processing_rules:
           - type: include_at_match
             name: include_anyconnect_logs
             pattern: .*(AnyConnect|113038|113039|716061|734001|751005|751025|722053|722054).*
      ```

    See the sample [cisco_secure_client.d/conf.yaml][6] for available configuration options.

    **Note**: Do not change the `source` and `service` values, as these parameters are integral to the pipeline's operation.

3. [Restart the Agent][3].

#### To Configure Syslog on FTD, Follow These Steps:

1. Select **Devices** > **Platform Settings** and create or edit an FTD policy.
2. Select **Syslog** > **Logging Setup**.
    <ol type="a">
      <li>Check the <b>Enable Logging</b> check box in order to enable logging.</li>
      <li>Click <b>Save</b>.</li>
    </ol>
3. Select **Syslog** > **Syslog Settings**.
    <ol type="a">
      <li>Check the <b>Enable Timestamp on Syslog Messages</b> checkbox in order to include timestamp in syslog messages.</li>
      <li>Select <b>RFC 5424 (yyyy-MM-ddTHH:mm:ssZ</b> from the Timestamp Format dropdown list.</li>
      <li>Click <b>Save</b>.</li>
    </ol>
4. Select **Syslog** > **Syslog Server**.
    <ol type="a">
      <li>Check the <b>Allow user traffic to pass when TCP syslog server is down</b> checkbox, to allow traffic if any syslog server that is using the TCP protocol is down.</li>
      <li>Click <b>Add</b> to add a new syslog server.</li>
      <ol type="i">
        <li>In the <b>IP Address</b> dropdown menu, select a network object that contains the IP address of the syslog server. If a network object is not created, click on the <b>plus (+)</b> button to create a new network object.</li>
        <li><b>Protocol</b>: Click on either TCP or UDP protocol for syslog communication.</li>
        <li><b>Port</b>: Enter the port number on which the Datadog agent is listening.</li>
        <li>Available Zones: From the <b>Available Zones</b> list, click on the interface/zone where the syslog server is reachable, then click <b>Add</b> to move it to the <b>Selected Zones/Interfaces</b> column.</li>
        <li>Click <b>OK</b>.</li>
      </ol>
      <li>Click <b>Save</b>.</li>
    </ol>
5. Go to **Deploy** > **Deployment** and deploy the policy to assigned devices. The changes are not active until you deploy them.
    ```

#### To Configure Syslog on ASA, Follow These Steps:

1. Connect to the **Cisco ASA CLI**.
2. Execute below command to enter privileged EXEC mode:
    ```
    enable
    ```
    <ol type="a">
      <li>Enter the password.</li>
    </ol>
3. Enable global configuration mode by executing below command:
    ```
    configure terminal
    ```
4. Enable logging by executing below command:
    ```
    logging enable
    ```
5. Configure syslog log forwarding: 

   (Replace the below placeholders with actual values in command)

   **interface_name**: interface that the syslog server is associated with

   **ip_address**: ip address of syslog server

   **port**: port on which the syslog server is listening.

    For UDP:
    ```
    logging host interface_name ip_address udp/port
    ```

    For TCP:
    ``` 
    logging host interface_name ip_address tcp/port
    ```

6. Set the logging level to debugging by executing this command:
    ```
    logging trap debugging
    ```

7. Execute below command which enables rfc5424 timestamp format in syslog:
    ```
    logging timestamp rfc5424
    ```

**Note**: The `port` value should be similar to the port provided in the `Log Collection` section.

### Validation

[Run the Agent's status subcommand][2] and look for `cisco_secure_client` under the Logs Agent section.

## Data Collected

### Log Collection

The Cisco Secure Client integration collects VPN client behavior, connection status, and authentication logs.

### Metrics

The Cisco Secure Client does not include any metrics.

### Events

The Cisco Secure Client integration does not include any events.

## Troubleshooting

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

   2. [Restart the Agent][3].

**Data is not being collected:**

Make sure that traffic is bypassed from the configured port if the firewall is enabled.

**Port already in use:**

If you see the **Port <PORT_NUMBER> Already in Use** error, see the following instructions. The example below is for a PORT_NUMBER equal to 514:

On systems using Syslog, if the Agent listens for logs on port 514, the following error can appear in the Agent logs: `Can't start UDP forwarder on port 514: listen udp :514: bind: address already in use`.

This error occurs because by default, Syslog listens on port 514. To resolve this error, take **one** of the following steps:

- Disable Syslog.
- Configure the Agent to listen on a different, available port.

Need help? Contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[3]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[4]: https://www.cisco.com/site/in/en/products/security/secure-client/index.html
[5]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install
[6]: https://github.com/DataDog/integrations-core/blob/master/cisco_secure_client/datadog_checks/cisco_secure_client/data/conf.yaml.example