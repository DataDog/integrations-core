# Agent Integration: cloudgen_firewall

## Overview

This integration monitors [cloudgen_firewall][1].

## Setup

### Installation

The cloudgen_firewall check is included in the [Datadog Agent][2] package.
Barracuda cloudGen Firewall installation is needed on your server.

### Configuration

1. Barracuda CloudGen Firewall with Administrative access.
2. DataDog Agent installed and running(server or container that can receive syslog).
3. Network Access between firewall and the dataDog agent (usually port 514 or custom).
4. Syslog support enabled in Datadog Agent (tcp/udp listener configured).

### Validation

1. Confirm Datadog Agent is listening on the right port (eg., 514)
    sudo netstat -tunlp | grep 514
OR, for TCP/UDP listeners:
    sudo lsof -i :514
2. Confirm logs are reaching to the Agent and check for specific log source.
    tail -f /var/log/datadog/syslog.log
(If file doesn't exists, verify that syslog logs are being written by your config).
3. Use tcpdump to confirm network traffic. On datadog Agent host:
    sudo tcpdump -i any port 514
You should see traffic from the cloudGen Firwewall IP address. if not, check firewall rules between cloudGen and Agent. Confirm the correct protocol (UDP/TCP) is being used on both sides.
4. Check Live Tail in Datadog. Filter by source and service as defined in conf.yaml.
5. Create a Test Log on the firewall by triggering an event.
6. Check parsing and tagging in datadog.
7. Use a Dashboard that is created to track volume over time.

## Data Collected

### Metrics

cloudgen_firewall does not include any metrics.

### Log Collection


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

    Change the `path` and `service` parameter values and configure them for your environment.

3. [Restart the Agent][4].

### Events

The cloudgen_firewall integration include recognizable events like messages (eg. login failed, rule hits). These can be surfaced as datadog events with parsing.

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: https://www.barracuda.com/products/network-protection/cloudgen-firewall
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/help/
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://app.datadoghq.com/integrations?search=barracuda_cloudgen_firewall
[6]: https://github.com/DataDog/integrations-core/blob/master/cloudgen_firewall/assets/service_checks.json

