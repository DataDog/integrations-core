# Agent Integration: Cisco ISE

## Overview

This integration collects [Cisco Identity Services Engine (ISE)][4] logs through the Datadog Agent.

Cisco ISE is a network access control platform. It decides whether users and devices can join the wired, wireless, or VPN network and what access they get (VLAN, downloadable ACL, Security Group Tag). It also authenticates network administrators on switches and routers through TACACS+. ISE sends its logs as syslog to a *Remote Logging Target*; this integration points that target at a Datadog Agent that listens on a UDP or TCP port.

### What this integration monitors

The integration collects ISE's logs for each kind of activity ISE controls:

| Activity | Logging Categories | What's collected |
|---|---|---|
| **Network access (RADIUS authentications)** | *Passed Authentications*, *Failed Attempts* | Who joined the network or failed to, with the user, the endpoint MAC address, the network device and port, the SSID, the site, the authentication method, the authorization result (VLAN, downloadable ACL, Security Group Tag), and the failure reason. |
| **Network sessions (RADIUS accounting)** | *RADIUS Accounting* | Session start, interim updates, and stop. They link each endpoint IP address to its user and MAC address. Requires RADIUS accounting on the network devices. |
| **Device administration (TACACS+)** | *Passed Authentications* and *Failed Attempts* (logins), *TACACS Accounting* (commands) | Administrator logins on switches and routers, their privilege level, and the commands they type. |
| **ISE administration** | *Administrative and Operational Audit* | ISE administrator logins and configuration changes. |
| **Endpoint profiling** | *Profiler* | The device type, operating system, and vendor ISE assigns to each endpoint. |
| **Guest and My Devices portals** | *Guest*, *MyDevices* | Guest self-registration and logins, and the devices employees register. |
| **Posture and quarantine** | *Posture and Client Provisioning Audit* | Posture results and quarantine (Adaptive Network Control) actions. |

### Supported versions

Cisco ISE 3.x (tested on 3.2).

## Setup

### Installation

The Cisco ISE integration is included in the [Datadog Agent][8] package. No additional installation is needed on the Agent host, and nothing is installed on ISE: ISE pushes its logs to the Agent, which must be reachable from the ISE nodes on the port you configure.

### Configuration

#### Configure the Datadog Agent

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in `datadog.yaml`:

    ```yaml
    logs_enabled: true
    ```

2. Edit the `cisco_ise.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory. Start from the sample [cisco_ise.d/conf.yaml][5]: uncomment the `logs` section and set the port. Both UDP and TCP are supported; TLS is not.

    ```yaml
    logs:
      - type: udp # or tcp
        port: <PORT>
        source: cisco-ise
    ```

    Keep the two `log_processing_rules` that follow in the sample: they mask secrets typed in TACACS+ commands (see [Sensitive data](#sensitive-data)). Do not change the `source` value, as it is integral to the pipeline's operation.

3. [Restart the Agent][3].

To filter or mask other messages before they leave the Agent, add [log processing rules][9] to the logs configuration.

#### Configure Cisco ISE

In Cisco ISE, add a Remote Logging Target for the Agent: UDP or TCP syslog (matching the Agent's `type`), the Agent host, and the port set above. Set its **Maximum Length** to **8192**; if your ISE version accepts less, use the highest value it accepts. ISE splits any event longer than this into several syslog messages, each a separate log, and ISE's default of 1024 splits most events.

Then attach the Logging Categories you want to collect to the target. For the list, see [What this integration monitors](#what-this-integration-monitors). ISE only sends the categories attached to a target.

### Validation

[Run the Agent's status subcommand][2] and look for `cisco_ise` under the Logs Agent section. In the [Log Explorer][6], search for `source:cisco-ise`.

## Data Collected

### Logs

The Cisco ISE integration collects ISE's syslog messages with `source:cisco-ise`, for the activity listed in [What this integration monitors](#what-this-integration-monitors).

#### Sensitive data

- **TACACS+ commands** are logged as typed, including secrets, for example `username admin secret 0 <password>`. The two `mask_sequences` rules in the sample configuration mask these secrets in the Agent, before the logs leave your network. They replace everything typed after any of these keywords in a command with `********`: `secret`, `password`, `key`, `key-string`, `community`, `pre-shared-key`, `auth`, or `priv`, including hyphenated forms such as `authentication-key`. The masking needs events that aren't split: if ISE splits an event between the keyword and the value, the value is sent unmasked. The rules only cover these keywords; to mask other values, add rules or use [Sensitive Data Scanner][7].
- **Guest portal messages** (Guest category, and guest logins) contain visitors' personal data: name, email address, phone number, company, and the person visited. Don't attach the Guest category if you don't need it, or use [Sensitive Data Scanner][7] to redact these fields.

### Metrics

The Cisco ISE integration does not include any metrics.

### Events

The Cisco ISE integration does not include any events.

### Service Checks

The Cisco ISE integration does not include any service checks.

## Uninstallation

In ISE, remove the Datadog target from the Logging Categories, or delete the Remote Logging Target. Then rename `cisco_ise.d/conf.yaml` to `cisco_ise.d/conf.yaml.example` and [restart the Agent][3].

## Troubleshooting

**Events are split into several logs:**

ISE splits an event longer than the Remote Logging Target's **Maximum Length** into several syslog messages, and each one becomes a separate log. Set **Maximum Length** to 8192, or to the highest value your ISE version accepts.

**Only some events arrive over UDP:**

Over UDP, events larger than about 1,500 bytes, such as most authentications, are sent as fragmented IP packets. If a firewall or NAT device between ISE and the Agent drops fragments, those events are lost while smaller ones, such as accounting messages, arrive. Allow fragments on that path, or use TCP.

**Permission denied while port binding:**

On Linux, the Agent can't listen on a port under 1024 without elevated permissions. Use a port above 1024 in the Agent and in the ISE target.

**Data is not being collected:**

Make sure that the firewall on the Agent host allows traffic to the configured port, and that the ISE target is enabled and attached to the Logging Categories.

**Port already in use:**

On systems running syslog, port 514 is usually taken. Configure the Agent to listen on a different, available port and use the same port in the ISE target.

## Support

Need help? Contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[3]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[4]: https://www.cisco.com/site/us/en/products/security/identity-services-engine/index.html
[5]: https://github.com/DataDog/integrations-core/blob/master/cisco_ise/datadog_checks/cisco_ise/data/conf.yaml.example
[6]: https://app.datadoghq.com/logs?query=source%3Acisco-ise
[7]: https://docs.datadoghq.com/security/sensitive_data_scanner/
[8]: https://app.datadoghq.com/account/settings/agent/latest
[9]: https://docs.datadoghq.com/agent/logs/advanced_log_collection/
