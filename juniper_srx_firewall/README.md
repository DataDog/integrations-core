## Overview

[Juniper SRX Firewall][3] secures your network edge, data center, and cloud applications by detecting and mitigating intrusions, malware, and other threats.

This integration parses the following log types:

- **Session Logs**: Track network traffic and session activities, including initiated and denied sessions, application-related traffic, and dropped packets.
- **Security Logs**: Monitor security events such as malware detections, intrusion attempts, DoS attacks, and content filtering activities.
- **Authentication Logs**: Capture authentication activities, including successful and failed login attempts.

Get detailed visibility into these logs with out-of-the-box dashboards, and strengthen security with prebuilt Cloud SIEM detection rules for proactive threat monitoring and response.

**Minimum Agent version:** 7.67.0

## Setup

### Installation

To install the Juniper SRX Firewall integration, run the following Agent installation command in your terminal. For more information, see the [Integration Management][4] documentation.

**Note**: This step is not necessary for Agent version >= 7.64.0.

```shell
sudo -u dd-agent -- datadog-agent integration install datadog-juniper_srx_firewall==1.0.0
```

### Configuration

#### Configure log collection

1. Log collection is disabled by default in the Datadog Agent. Enable it in `datadog.yaml`:

   ```yaml
   logs_enabled: true
   ```

2. Add the following configuration block to your `juniper_srx_firewall.d/conf.yaml` file to start collecting logs. See the [sample `conf.yaml`][6] for available configuration options.

   ```yaml
   logs:
     - type: udp
       port: <PORT>
       source: juniper-srx-firewall
       service: juniper-srx-firewall
   ```

   **Note**:

   - `PORT`: Specify the UDP port that Datadog will listen on (default: 514).
   - Do not change the `service` and `source` values, as they are integral to proper log pipeline processing.

3. [Restart the Agent][2].

#### Configure syslog message forwarding from Juniper SRX Firewall

1. Log in to the Juniper SRX Firewall CLI.

2. Enter configuration mode:
   ```shell
   configure
   ```

3. To send logs to the Datadog Agent, execute the following commands:
   ```shell
   set system syslog host <IP-ADDRESS> any any
   set system syslog host <IP-ADDRESS> port <PORT>
   set system syslog host <IP-ADDRESS> structured-data brief
   ```
   **Note**:
   - Replace `<IP-ADDRESS>` with the Datadog Agent's IP address.
   - Replace `<PORT>` with the same port configured in [Log Collection][7].

4. Verify if `Security Logging` is enabled:
   ```shell
   show security log mode
   ```
   If enabled, the output will display either `mode stream;` or `mode event-stream;`

5. If `Security Logging` is enabled, configure log streaming:
   ```shell
   set security log stream <NAME> format sd-syslog
   set security log stream <NAME> category all
   set security log stream <NAME> host <IP-ADDRESS>
   set security log stream <NAME> host port <PORT>
   set security log transport protocol udp
   ```

6. Apply and exit the configuration:
   ```
   commit
   exit
   ```

### Validation

[Run the Agent's status subcommand][5] and look for `juniper_srx_firewall` under the **Checks** section.

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

### Permission denied while port binding

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

### Data is not being collected

Ensure firewall settings allow traffic through the configured port.

### Port already in use

On systems running Syslog, the Agent may fail to bind to port 514 and display the following error: 
   
    Can't start UDP forwarder on port 514: listen udp :514: bind: address already in use

This error occurs because Syslog uses port 514 by default. 

To resolve:
  - Disable Syslog, OR
  - Configure the Agent to listen on a different, available port.

For further assistance, contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[3]: https://www.juniper.net/us/en/products/security/srx-series.html
[4]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/juniper_srx_firewall/datadog_checks/juniper_srx_firewall/data/conf.yaml.example
[7]: https://docs.datadoghq.com/integrations/juniper_srx_firewall/#configure-log-collection
