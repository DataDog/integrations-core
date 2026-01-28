## Overview

[Cisco Secure Client][4] (formerly AnyConnect) provides secure, encrypted VPN access for users connecting to internal resources. It ensures reliable remote connectivity, and handles sessions, licensing, and client version compatibility to maintain consistent security across multiple devices.

Integrate Cisco Secure Client with Datadog to gain insights into AnyConnect logs using pre-built dashboard visualizations. Datadog uses its built-in log pipelines to parse and enrich these logs, facilitating easy search and detailed insights. The integration can also be used for Cloud SIEM detection rules for enhanced monitoring and security.

**Minimum Agent version:** 7.77.0

**Disclaimer**: Your use of this integration, which may collect data that includes personal information, is subject to your agreements with Datadog. Cisco is not responsible for the privacy, security or integrity of any end-user information, including personal data, transmitted through your use of the integration.

## Setup

### Configuration

#### Enable log collection

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in the `datadog.yaml` file with:
    ```yaml
    logs_enabled: true
    ```

2. Add the following configuration block to your `cisco_secure_client.d/conf.yaml` file to start collecting your Cisco Secure Client logs:

      ```yaml
      logs:
        - type: tcp # or udp
          port: <PORT>
          service: cisco-secure-client
          source: cisco-secure-client
          log_processing_rules:
           - type: include_at_match
             name: include_anyconnect_logs
             pattern: .*(AnyConnect|anyconnect|113038|113039|734001|751025|722053|722054).*
      ```

    See the sample [`cisco_secure_client.d/conf.yaml`][6] for available configuration options.

    **Note**: Do not change the `source` and `service` values, as these parameters are integral to the pipeline's operation.

3. [Restart the Agent][3]. 


<br>
<b>Note</b>: To forward Cisco Secure Client logs, you must configure syslog on the Cisco firewall platform that you're using with Cisco Secure Client (FTD, Meraki, or ASA; see below for instructions for each platform).
</br>

#### Configure Syslog on Cisco FTD Firewall using FMC

1. Connect to the Cisco Firewall Management Center (FMC) platform.
2. Select **Devices** > **Platform Settings** and create or edit an FTD policy.
3. Select **Syslog** > **Logging Setup**.
    1. Check the **Enable Logging** checkbox.
    2. Click **Save**.
4. Select **Syslog** > **Syslog Settings**.
    1. Check the **Enable Timestamp on Syslog Messages** checkbox.
    2. Select **RFC 5424 (yyyy-MM-ddTHH:mm:ssZ)** from the Timestamp Format dropdown list.
    3. Click **Save**.
5. Select **Syslog** > **Syslog Server**.
    1. Check the **Allow user traffic to pass when TCP syslog server is down** checkbox.
    2. Click **Add** to add a new syslog server:

        - **IP Address**: In the dropdown menu, select a network object that contains the IP address of the syslog server. If a network object is not created, click on the **plus (+)** to create a new network object.
        - **Protocol**: Click on either TCP or UDP protocol for syslog communication.
        - **Port**: Enter the port number on which the Datadog Agent is listening.
        - **Available Zones**: From the **Available Zones** list, click on the interface or zone where the syslog server is reachable, then click **Add** to move it to the **Selected Zones/Interfaces** column.

    3. Click **OK**, then click **Save**.
6. Go to **Deploy** > **Deployment** and deploy the policy to assigned devices. The changes are not active until you deploy them.

**Note**: The `Port` value should be similar to the port provided in the `Log Collection` section.

#### Configure Syslog on Cisco Meraki Firewall

1. Log in to Cisco Meraki.
2. Navigate to **Network-wide** > **Configure** > **General**.
3. Navigate to **Reporting** > **Syslog Servers**.
4. Click on **Add a syslog server**.
5. Set the following configuration parameters:
    - **Server Address**: IP address of the syslog server 
    - **Port**: port on which the syslog server is listening
    - **Protocol**: select TCP or UDP from the dropdown
    - **Roles**: select **Appliance Event Log** from the dropdown
6. Click **Update syslog servers** to save the configuration.

**Note**: The `Port` value should be similar to the port provided in the `Log Collection` section.

#### Configure Syslog on Cisco ASA Firewall

1. Connect to the Cisco ASA CLI.
2. Enter the privileged EXEC mode by running the following; enter the password when prompted:
    ```
    enable
    ```
3. Enable global configuration mode:
    ```
    configure terminal
    ```
4. Enable logging:
    ```
    logging enable
    ```
5. Configure syslog log forwarding, replacing the placeholders with the relevant values:

   * `<interface_name>`: the interface that the syslog server is associated with
   * `<ip_address>`: the IP address of the syslog server
   * `<port>`: the port where the syslog server is listening

    For UDP:
    ```
    logging host <interface_name> <ip_address> udp/<port>
    ```

    For TCP:
    ``` 
    logging host <interface_name> <ip_address> tcp/<port>
    ```

6. Set the logging level to debug:
    ```
    logging trap debugging
    ```

7. Enable rfc5424 timestamp format in syslog:
    ```
    logging timestamp rfc5424
    ```

**Note**: The `port` value should be similar to the port provided in the `Log Collection` section.

### Validation

[Run the Agent's status subcommand][2] and look for `cisco_secure_client` under the Logs Agent section.

## Data Collected

### Log Collection

The Cisco Secure Client integration collects AnyConnect logs.

### Metrics

The Cisco Secure Client integration does not include any metrics.

### Events

The Cisco Secure Client integration does not include any events.

## Troubleshooting

**Permission denied while port binding:**

Binding to a port number under 1024 requires elevated permissions. If you see a **Permission denied** error while port binding in the Agent logs:

1. Grant access to the port using the `setcap` command:

    ```shell
    sudo setcap CAP_NET_BIND_SERVICE=+ep /opt/datadog-agent/bin/agent/agent
    ```

    **Note**: Re-run this `setcap` command every time you upgrade the Agent.

2. Verify the setup is correct by running the `getcap` command:

    ```shell
    sudo getcap /opt/datadog-agent/bin/agent/agent
    ```

    You should see the following output:

    ```shell
    /opt/datadog-agent/bin/agent/agent = cap_net_bind_service+ep
    ```

3. [Restart the Agent][3].

**Data is not being collected:**

Make sure that traffic is bypassed from the configured port if the firewall is enabled.

**Port already in use:**

On systems using syslog, if the Agent listens for logs on port 514, the following error can appear in the Agent logs: `Can't start UDP forwarder on port 514: listen udp :514: bind: address already in use`.

By default, syslog listens on port 514. To resolve this error, take **one** of the following steps:

- Disable syslog, or 
- Configure the Agent to listen on a different, available port.

Need help? Contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[3]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[4]: https://www.cisco.com/site/in/en/products/security/secure-client/index.html
[5]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install
[6]: https://github.com/DataDog/integrations-core/blob/master/cisco_secure_client/datadog_checks/cisco_secure_client/data/conf.yaml.example