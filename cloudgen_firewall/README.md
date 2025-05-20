# Agent Check: cloudgen_firewall

## Overview

This check monitors [cloudgen_firewall][1].

Include a high level overview of what this integration does:
- Barracuda CloudGen Firewall is a next-generation firewall (NGFW) that combines traditional firewall functions with advanced security and networking features to protect and optimize distributed networks
- This integration enables real-time security visibility, faster incident response, and smarter analytics by combining Barracuda's threat prevention with Datadog's modern observability platform.
- The integration will monitor traffic, threats, authentication, VPN, system and so on enriching them with real-time analytics and alerts in Datadog. This helps customer in security Posture, incident detection & response time and enhance operational awareness. 

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

### Events

cloudgen_firewall include recognizable events like messages (eg. login failed, rule hits). These can be surfaced as datadog events with parsing.

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: https://www.barracuda.com/products/network-protection/cloudgen-firewall
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/help/