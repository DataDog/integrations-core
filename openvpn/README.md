# Agent Integration: OpenVPN

## Overview

[OpenVPN][4] is a free, open-source protocol that creates secure connections between devices over the internet. It's used to create virtual private networks (VPNs).

This integration enriches and ingests the following events:

- **Authentication Events**: Represents user login attempts, including successful and failed authentications.
- **Connection Events**: Represents instances when a client establishes or disconnects a VPN session.

This integration seamlessly collects all of the above listed logs, channeling them into Datadog for analysis. Leveraging the built-in logs pipeline, these logs are parsed and enriched, enabling effortless search and analysis. The OpenVPN integration provides insight into authentication and connection events through the out-of-the-box dashboards. Additionally, it includes ready-to-use Cloud SIEM detection rules for enhanced monitoring and security.

**Minimum Agent version:** 7.67.0

## Setup

### Installation

To install the OpenVPN integration, run the following Agent installation command and the steps below for log collection. For more information, see the [Integration Management][5] documentation.

**Note**: This step is not necessary for Agent version >= 7.65.0.

Linux command:

  ```shell
  sudo -u dd-agent -- datadog-agent integration install datadog-openvpn==1.0.0
  ```

### Configuration

#### Log collection

1. Collecting logs is disabled by default in the Datadog Agent. Enable log collection in your `datadog.yaml`:

    ```yaml
    logs_enabled: true
    ```

2. Add this configuration block to your `openvpn.d/conf.yaml` file to start collecting your OpenVPN logs.

    See the sample [openvpn.d/conf.yaml][7] for available configuration options. The appropriate protocol (either TCP or UDP) should be chosen based on the OpenVPN syslog forwarding configuration.

      ```yaml
      logs:
       - type: tcp/udp
         port: <PORT>
         service: openvpn
         source: openvpn
      ```

      Note:
      - PORT: Port should be similar to the port provided in **Configure syslog message forwarding from openvpn server**.
      - It is recommended not to change the service and source values, as these parameters are integral to the pipeline's operation.

3. [Restart the Agent][1].

#### Configure Syslog Message Forwarding from OpenVPN Server

   - Please follow provided link steps to configure syslog over OpenVPN: [Configure syslog over OpenVPN][6] 

### Validation

[Run the Agent's status subcommand][2] and look for `openvpn` under the Checks section.

## Data Collected

### Logs

The OpenVPN integration collects Authentication Events and Connection Events.

### Metrics

The OpenVPN integration does not include any metrics.

### Events

The OpenVPN integration does not include any events.

### Service Checks

The OpenVPN integration does not include any service checks.

## Troubleshooting

### OpenVPN

**Permission denied while port binding:**

If you see a **Permission denied** error while port binding in the Agent logs, see the following instructions:

   1. Binding to a port number under 1024 requires elevated permissions.

      - Grant access to the port using the `setcap` command:

         ```shell
         sudo setcap CAP_NET_BIND_SERVICE=+ep /opt/datadog-agent/bin/agent/agent
         ```

      - Verify the setup is correct by running the `getcap` command:

         ```shell
         sudo getcap /opt/datadog-agent/bin/agent/agent
         ```

         Example of the expected output:

         ```shell
         /opt/datadog-agent/bin/agent/agent = cap_net_bind_service+ep
         ```

         **Note**: Re-run this `setcap` command every time you upgrade the Agent.

   2. [Restart the Agent][1].

**Data is not being collected:**

Make sure that traffic is bypassed from the configured port if the firewall is enabled.

**Port already in use:**

If you see the **Port <PORT-NO\> Already in Use** error, see the following instructions. The example below is for PORT-NO = 514:

On systems using Syslog, if the Agent listens for events on port 514, the following error can appear in the Agent logs: `Can't start UDP forwarder on port 514: listen udp :514: bind: address already in use`.

This error occurs because Syslog listens on port 514 by default. To resolve it, use one of the following steps:

- Disable Syslog.
- Configure the Agent to listen on a different, available port.

**Troubleshooting OpenVPN Logs Not Appearing in Datadog**

If OpenVPN logs are not appearing in Datadog after setup, try restarting **openvpnas** and **rsyslog** services.

- Run the following command to restart openvpnas service:
   ```shell
   service openvpnas restart
   ```
- Run the following command to restart rsyslog service:
   ```shell
   service rsyslog restart
   ```

For any further assistance, contact [Datadog support][3].

[1]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[3]: https://docs.datadoghq.com/help/
[4]: https://openvpn.net/access-server/
[5]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install
[6]: https://openvpn.net/as-docs/tutorials/tutorial--syslog.html#option-2--redirect-access-server-logs-to-an-external-syslog-server
[7]: https://github.com/DataDog/integrations-core/blob/master/openvpn/datadog_checks/openvpn/data/conf.yaml.example