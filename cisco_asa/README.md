## Overview

[Cisco ASA][4] is a robust firewall platform that provides enterprise-class protection with high availability and scalable performance. It adapts to evolving security needs and supports dynamic routing for modern networks and data centers.

Integrate Cisco ASA with Datadog to gain insights into threat detection, user authentication, user authorization, user management, dynamic traffic insights, connection insights, ARP collision insights, application firewall, transparent firewall and identity firewall using pre-built dashboard visualizations. Datadog uses its built-in log pipelines to parse and enrich these logs, facilitating easy search and detailed insights. The integration can also be used for Cloud SIEM detection rules for enhanced monitoring and security.

**Disclaimer**: Your use of this integration, which may collect data that includes personal information, is subject to your agreements with Datadog. Cisco is not responsible for the privacy, security or integrity of any end-user information, including personal data, transmitted through your use of the integration.

## Setup

### Configuration

#### Enable log collection

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in `datadog.yaml`:
    ```yaml
    logs_enabled: true
    ```

2. Add this configuration block to your `cisco_asa.d/conf.yaml` file to start collecting your Cisco ASA logs.

      ```yaml
      logs:
       - type: tcp # or 'udp'
         port: <PORT>
         service: cisco-asa
         source: cisco-asa
      ```

    See the sample [`cisco_asa.d/conf.yaml`][6] file for available configuration options.

    **Note**: Do not change the `source` and `service` values, as these parameters are integral to the pipeline's operation.

3. [Restart the Agent][3].

#### Syslog Configuration from Cisco ASA CLI: 

1. Connect to the Cisco ASA CLI.
2. Enter privileged EXEC mode by running:
    ```shell
    enable
    ```

    When prompted, enter the password.

3. Enable global configuration mode:
    ```shell
    configure terminal
    ```
4. Enable logging:
    ```shell
    logging enable
    ```
5. Configure syslog log forwarding: 

    Replace the placeholders with actual values:
    - **interface_name**: interface that the syslog server is associated with
    - **ip_address**: IP address of the syslog server
    - **port**: port where the syslog server is listening

    For UDP:
    ```shell
    logging host <interface_name> <ip_address> udp/<port>
    ```
    For TCP:
    ```shell
    logging host <interface_name> <ip_address> tcp/<port>
    ```
6. Set logging level to debugging:
    ```shell
    logging trap debugging
    ```
7. Enable RFC 5424 timestamp format:
    ```shell
    logging timestamp rfc5424
    ```

**Note**: The `port` value should be similar to the port provided in the `Log Collection` section.

### Validation

[Run the Agent's status subcommand][2] and look for `cisco_asa` under the Logs Agent section.

## Data Collected

### Logs

The Cisco ASA integration collects threat detection, user authentication, user authorization, user management, dynamic traffic insights, connection insights, ARP collision insights, application firewall, transparent firewall, and identity firewall logs.

### Metrics

The Cisco ASA does not include any metrics.

### Events

The Cisco ASA integration does not include any events.

## Troubleshooting

**Permission denied while port binding:**

If you see a **Permission denied** error while port binding in the Agent logs, see the following instructions:

1. Binding to a port number under 1024 requires elevated permissions. Grant access to the port using the `setcap` command:

    1. Grant access to the port using the `setcap` command:

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

2. [Restart the Agent][3].

**Data is not being collected:**

Make sure that traffic is bypassed from the configured port if the firewall is enabled.

**Port already in use:**

If you see the **Port <PORT_NUMBER> Already in Use** error, see the following instructions. The example below is for a PORT_NUMBER equal to 514:

On systems using syslog, if the Agent listens for logs on port 514, the following error can appear in the Agent logs: `Can't start UDP forwarder on port 514: listen udp :514: bind: address already in use`.

This error occurs because by default, Syslog listens on port 514. To resolve this error, take **one** of the following steps:

- Disable syslog, or
- Configure the Agent to listen on a different, available port.

Need help? Contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[3]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[4]: https://www.cisco.com/c/en_in/products/security/adaptive-security-appliance-asa-software/index.html
[5]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install
[6]: https://github.com/DataDog/integrations-core/blob/master/cisco_asa/datadog_checks/cisco_asa/data/conf.yaml.example
