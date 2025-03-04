## Overview

[Juniper SRX Firewall][3] protects your network edge, data center network, and cloud applications. It offers accurately predicting intrusions, malware, and other threats.

This integration parses the following types of logs:

- **Session Logs** : Logs provide information about network traffic and session activities in the Juniper SRX Firewall, offering details on initiated and denied sessions, application-related traffic, and dropped packets.
- **Security Logs** : Logs provide information about security events on the Juniper SRX Firewall, offering details on malware detections, intrusion attempts, DoS attacks, and content filtering activities.
- **Authentication Logs** : Logs provide information about authentication activities on the Juniper SRX Firewall, capturing details of successful and failed login attempts.

Visualize detailed insights into these logs through the out-of-the-box dashboards. Additionally, ready-to-use Cloud SIEM detection rules are available to help you monitor and respond to potential security threats effectively.

## Setup

### Installation

To install the Juniper SRX Firewall integration, run the following Agent installation command in your terminal, then complete the configuration steps below. For more information, see the [Integration Management][4] documentation.

**Note**: This step is not necessary for Agent version >= 7.59.0.

```shell
sudo -u dd-agent -- datadog-agent integration install datadog-juniper_srx_firewall==1.0.0
```

### Configuration

#### Log collection

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in `datadog.yaml`:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `juniper_srx_firewall.d/conf.yaml` file to start collecting your logs.

   See the sample [juniper_srx_firewall.d/conf.yaml][6] for available configuration options.

   ```yaml
   logs:
     - type: udp
       port: <PORT>
       source: juniper-srx-firewall
       service: juniper-srx-firewall
   ```

   **Note**:

   - `PORT`: Port should be similar to the port provided in **Configure syslog message forwarding from Juniper SRX Firewall** section.
   - It is recommended not to change the service and source values, as these parameters are integral to the pipeline's operation.

3. [Restart the Agent][2].

#### Configure syslog message forwarding from Juniper SRX Firewall

1. Log in to your Juniper SRX Firewall CLI.
2. To enter configuration mode, execute the following command:
   ```
   configure
   ```
3. To send logs to a syslog server, execute the following commands:
   ```
   set system syslog host <SYSLOG-SERVER-IP> any any
   set system syslog host <SYSLOG-SERVER-IP> port <PORT>
   set system syslog host <SYSLOG-SERVER-IP> structured-data brief
   set system syslog time-format millisecond
   set system syslog time-format year
   ```
4. If `Security Logging` is enabled, then execute the following commands:
   ```
   set security log mode stream
   set security log utc-timestamp
   set security log stream <NAME> format sd-syslog
   set security log stream <NAME> category all
   set security log stream <NAME> host <SYSLOG-SERVER-IP>
   set security log stream <NAME> host port <PORT>
   set security log transport protocol udp
   ```
5. To Apply the configuration, execute the following command:
   ```
   commit
   ```

### Validation

[Run the Agent's status subcommand][5] and look for `juniper_srx_firewall` under the Checks section.

## Data Collected

### Log

| Format                    | Event Types                                      |
| ------------------------- | ------------------------------------------------ |
| Structured-Data(RFC 5424) | Session Logs, Security Logs, Authentication Logs |

### Metrics

The Juniper SRX Firewall integration does not include any metrics.

### Events

The Juniper SRX Firewall integration does not include any events.

### Service Checks

The Juniper SRX Firewall integration does not include any service checks.

## Troubleshooting

**Permission denied while port binding:**

If you see a **Permission denied** error while port binding in the Agent logs:

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

3. [Restart the Agent][2].

**Data is not being collected:**

Ensure traffic is bypassed from the configured port if the firewall is enabled.

**Port already in use:**

If you see the **Port <PORT_NUMBER> Already in Use** error, see the following instructions. The following example is for port 514:

- On systems using Syslog, if the Agent listens for events on port 514, the following error can appear in the Agent logs: `Can't start UDP forwarder on port 514: listen udp :514: bind: address already in use`. This error occurs because by default, Syslog listens on port 514. To resolve this error, take **one** of the following steps:
  - Disable Syslog.
  - Configure the Agent to listen on a different, available port.

For further assistance, contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[3]: https://www.juniper.net/us/en/products/security/srx-series.html
[4]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/juniper_srx_firewall/datadog_checks/juniper_srx_firewall/data/conf.yaml.example
