# Agent Integration: cloudgen_firewall

## Overview

This integration monitors [cloudgen_firewall][1].

## Setup
1. Collecting logs is disabled by default in the Datadog Agent. Enable it in the `datadog.yaml` file with:

    ```yaml
      logs_enabled: true
    ```

2. Add this configuration block to your `cloudgen_firewall.d/conf.yaml` file to start collecting your cloudgen_firewall logs:

    ```yaml
      logs:
        - type: file
          path:  /var/log/cloudgen_firewall.log
          source: cloudgen_firewall
          service: <SERVICE_NAME>
    ```

    Change the `path` and `service` parameter values for your environment.

3. [Restart the Agent][4].

### Installation

The cloudgen_firewall check is included in the [Datadog Agent][2] package.

### Prerequisites

1. Administrative access to Barracuda CloudGen Firewall installed on your server.
2. The Datadog Agent installed and running (on a server or container that can receive syslog messages).
3. Network Access between the firewall and the Datadog Agent (usually port 514, but may be a custom value).
4. Syslog support enabled in the Datadog Agent (with a TCP or UDP  listener configured).

### Validation

1. Confirm the Datadog Agent is listening on the correct port (`514` in the following examples)
    `sudo netstat -tunlp | grep 514`
    If using TCP and UDP listeners, use the following command:
    `sudo lsof -i :514`
2. Confirm logs are reaching the Agent from the correct log source.
    `tail -f /var/log/datadog/syslog.log`
**Note**: If the file doesn't exist, verify that syslog logs are being written by your configuration.
3. Use the tcpdump command to confirm network traffic. On the Datadog Agent host:
    `sudo tcpdump -i any port 514`
After running this command, you should see traffic from the CloudGen Firewall IP address. If you don't see any such traffic, check the firewall rules between CloudGen and the Datadog Agent. Confirm the correct protocol (UDP or TCP) is being used on both sides.
4. Check the Datadog [Live Tail][7] in Datadog for logs from the source and service you defined in the `conf.yaml` file.
5. After following these steps, you can create a test log on the firewall by triggering an event.
6. Check for tags or facets to use them for better filtering based on the required data.

### Metrics

cloudgen_firewall does not include any metrics.

### Log collection
## Data Collected
The Barracuda CloudGen Firewall logs contain key information such as the event timestamp, source and destination IPs and ports, protocol used, firewall action (allow/deny), the matched rule name, user identity (if available), log type (e.g., firewall, VPN, authentication), network interface, device name, and status of the operation, all of which help monitor traffic behavior, access control, and system activity and many more which are collected by DataDog.


### Events

The cloudgen_firewall integration includes log events such as failed logins and rule hits.

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: https://www.barracuda.com/products/network-protection/cloudgen-firewall
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/help/
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://app.datadoghq.com/integrations?search=barracuda_cloudgen_firewall
[6]: https://github.com/DataDog/integrations-core/blob/master/cloudgen_firewall/assets/service_checks.json
[7]: https://app.datadoghq.com/logs/livetail
