# Agent Integration: barracuda_secure_edge

## Overview

Barracuda Secure Edge is a unified Secure Access Service Edge (SASE) platform that includes Next-Generation Firewall (NGFW), zero trust, and secure Software-Defined Wide Area Network (SD-WAN) capabilities. This integration allows you to collect and analyze logs from your [barracuda_secure_edge][4] deployment to monitor security events, network traffic, and system activity.

## Setup
### Prerequisites

- Administrative access to Barracuda Secure Edge installed on your server.
- The Datadog Agent installed and running (on a server or container that can receive syslog messages).
- Network Access between the firewall and the Datadog Agent (usually port 514, but may be a custom value).
- Syslog support enabled in the Datadog Agent (with a TCP or UDP  listener configured).

### Setup configurations
1. Collecting logs is disabled by default in the Datadog Agent. Enable it in the `datadog.yaml` with:

    ```yaml
      logs_enabled: true
    ```
2. Add this configuration block to your `secure_edge.d/conf.yaml` to start collecting your Secure Edge logs:

    ```yaml
      logs:
        - type: file
          path:  /var/log/secure_edge.log
          source: secure_edge
          service: <SERVICE_NAME>
    ```

    Change the `path` and `service` parameter values for your environment.

3. [Restart the Agent][3].

### Installation

The barracuda_secure_edge check is included in the [Datadog Agent][2] package.

### Validation

1. Confirm the Datadog Agent is listening on the correct port (`514` in the following examples)
    `sudo netstat -tunlp | grep 514`
    If using TCP and UDP listeners, use the following command:
    `sudo lsof -i :514`
2. Confirm logs are reaching the Agent from the correct log source.
    `tail -f /var/phion/logs/*.log`
**Note**: If the file doesn't exist, verify that syslog logs are being written to a file by your configuration.
3. Use the tcpdump command to confirm network traffic. On the Datadog Agent host:
    `sudo tcpdump -i any port 514`
After running this command, you should see traffic from the Secure Edge IP address. If you don't see any such traffic, check the firewall rules between Secure Edge and the Datadog Agent. Confirm the correct protocol (UDP or TCP) is being used on both sides.
4. Check the Datadog [Live Tail][5] in Datadog for logs from the source and service you defined in the `conf.yaml` file.
5. After following these steps, you can create a test log on the firewall by triggering an event.
6. Check for tags or facets to use them for better filtering based on the required data.

## Data Collected
### Metrics
Barracuda_Secure_Edge does not include any metrics.

### Events
The Barracuda Secure Edge integration does not include any events.

### Logs
The Barracuda Secure Edge integration collects logs containing the following types of information:
- **Security Events**: Firewall actions (allow/deny), rule matches, and security policy violations
- **Network Traffic**: Source and destination IPs/ports, protocols, and network interfaces
- **Authentication**: User login attempts, successes, and failures
- **VPN Activity**: VPN connection events and status
- **System Events**: Device status, configuration changes, and system health

## Troubleshooting

Need help? Contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: /account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[4]: https://www.barracuda.com/products/network-protection/secureedge
[5]: /logs/livetail