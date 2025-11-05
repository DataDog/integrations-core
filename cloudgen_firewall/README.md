# Agent Integration: cloudgen_firewall

## Overview

Barracuda CloudGen Firewall is a next-generation firewall (NGFW) family from Barracuda Networks designed to protect and optimize modern, distributed networks whether on-premises, in the cloud, or across hybrid environments. This integration monitors [cloudgen_firewall][1].

## Setup

### Prerequisites

1. Administrative access to Barracuda CloudGen Firewall installed on your server.
2. The Datadog Agent installed and running (on a server or container that can receive syslog messages).
3. Network Access between the firewall and the Datadog Agent (usually port 514, but may be a custom value).
4. Syslog support enabled in the Datadog Agent (with a TCP or UDP listener configured).

### Validation

1. Confirm the Datadog Agent is listening on the correct port (`514` in the following examples):

    `sudo netstat -tunlp | grep 514`

    If using TCP and UDP listeners, use the following command:

    `sudo lsof -i :514`

2. Confirm logs are reaching the Agent from the correct log source:

    `tail -f /var/log/datadog/syslog.log`

    **Note**: If the file doesn't exist, verify that syslog logs are being written by your configuration.

3. Use the tcpdump command to confirm network traffic on the Datadog Agent host:

    `sudo tcpdump -i any port 514`
    
After running this command, you should see traffic from the CloudGen Firewall IP address. If you don't see any such traffic, check the firewall rules between CloudGen and the Datadog Agent. Confirm the correct protocol (UDP or TCP) is being used on both sides.

### Configuration

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in the `datadog.yaml` file with:

    ```yaml
      logs_enabled: true
    ```

2. Add this configuration block to your `cloudgen_firewall.d/conf.yaml` file to start collecting your cloudgen_firewall logs:

    ```yaml
      logs:
        - type: file
          path: /var/log/cloudgen_firewall.log
          source: cloudgen_firewall
          service: <SERVICE_NAME>
    ```

    Change the `path` and `service` parameter values for your environment.

3. [Restart the Agent][4].


### Installation

The cloudgen_firewall check is included in the [Datadog Agent][2] package.

## Data collected

### Metrics

The Barracuda CloudGen Firewall integration does not include any metrics.

### Logs

The Barracuda CloudGen Firewall logs contain key information such as the event timestamp, source and destination IPs and ports, protocol used, firewall action (allow or deny), the matched rule name, user identity (if available), log type (such as firewall, VPN, authentication), network interface, device name, status of the operation, and many more. This helps you to monitor traffic behavior, access control, and system activity.

### Events

The cloudgen_firewall integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: https://www.barracuda.com/products/network-protection/cloudgen-firewall
[2]: /account/settings/agent/latest
[3]: https://docs.datadoghq.com/help/
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: /integrations?search=barracuda_cloudgen_firewall
