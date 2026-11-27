# Agent Integration: Cisco ISE

## Overview

This integration collects [Cisco Identity Services Engine (ISE)][4] logs through the Datadog Agent.

Cisco ISE is a network access control platform. It decides whether users and devices can join the wired, wireless, or VPN network and what access they get (VLAN, downloadable ACL, Security Group Tag). It also authenticates network administrators on switches and routers through TACACS+. ISE sends its logs as syslog to a *Remote Logging Target*; this integration points that target at a Datadog Agent that listens on a UDP or TCP port. Datadog's log pipeline parses the logs into Datadog standard attributes and `cisco_ise.*` attributes.

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

In Cisco ISE, add a Remote Logging Target for the Agent: UDP or TCP syslog (matching the Agent's `type`), the Agent host, and the port set above. Set its **Maximum Length** to **8192**; if your ISE version accepts less, use the highest value it accepts. ISE splits any event longer than this into several syslog messages, each a separate log. Only the first one is parsed, so fields such as the identity group or the endpoint MAC address are missing. ISE's default of 1024 splits most events.

Then attach the Logging Categories you want to collect to the target. For the list, see [What this integration monitors](#what-this-integration-monitors). ISE only sends the categories attached to a target.

### Validation

[Run the Agent's status subcommand][2] and look for `cisco_ise` under the Logs Agent section. In the [Log Explorer][6], search for `source:cisco-ise`.

## Data Collected

### Logs

The Cisco ISE integration collects ISE's syslog messages and parses them with the `cisco-ise` log pipeline:

- The syslog header gives the ISE node (`syslog.hostname`, also copied to `cisco_ise.node`), the Logging Category (`cisco_ise.category`), and the message ID and segment numbers.
- The message body gives the event time with milliseconds, the message code (`cisco_ise.message_code`, for example `5200` for a passed authentication), the severity, and ISE's own fields. The log status comes from the syslog priority, which ISE sets from its severity, also on messages split into segments.
- ISE's fields keep their names under `cisco_ise.attributes.*` (for example `cisco_ise.attributes.NetworkDeviceName`, `cisco_ise.attributes.FailureReason`), and the authorization result `Response={...}` is parsed under `cisco_ise.response.*`.
- Derived fields: the site levels, from the device's Location group in ISE (`Location`, such as `Location#All Locations#Spain#Madrid`, split into `cisco_ise.site.level1` to `level5` without the `All Locations` root), the endpoint MAC address normalized to `aa:bb:cc:dd:ee:ff` (`cisco_ise.endpoint.mac`, from whichever MAC field the message has, such as `Calling-Station-ID` or the profiler's `EndpointMacAddress`; ISE's original value is in `cisco_ise.endpoint.mac_raw`), and the TACACS+ command (`cisco_ise.tacacs.command`, `cisco_ise.tacacs.command_name`).
- Authorization result, from `Response={...}`: the VLAN (`cisco_ise.authorization.vlan`), the downloadable ACL (`cisco_ise.authorization.dacl`), and the Security Group Tag as ISE logs it, in hexadecimal (`cisco_ise.authorization.sgt`, for example `0004-00`).
- The SSID of wireless logins (`cisco_ise.ssid`), taken from ISE's `SSID` field when it has the form `<access point MAC>:<SSID>`.
- Profiler messages (`80002`): the endpoint vendor (`cisco_ise.attributes.EndpointOUI`) and ISE's list of endpoint properties as one string (`cisco_ise.endpoint.properties`).
- Standard attributes: `usr.name`, `network.client.ip` (the endpoint or administrator IP; for guest and My Devices portal messages, the IP of the browser as ISE saw it), and `evt.name` (ISE's message class, for example `Passed-Authentication` or `Failed-Attempt`).

ISE logs unknown users as `INVALID`, so failed logins by non-existing users are grouped under `@usr.name:INVALID`. For downloadable ACL requests (`5232`), ISE puts the ACL name (`#ACSACL#-...`) in `UserName`; it is not mapped to `usr.name`.

ISE escapes commas inside some values with a backslash, and the backslash stays in the attribute: for example `cisco_ise.attributes.EndpointOUI` is `Cisco Systems\, Inc`. Search these values with a wildcard, such as `@cisco_ise.attributes.EndpointOUI:Cisco*`.

The integration includes the **Cisco ISE Overview** dashboard, built on these logs. Its widgets query standard indexes: logs stored only in Flex Logs don't appear in it.

#### Finding failed logins

ISE has no single success or failure field, so the pipeline keeps the values ISE sends and doesn't classify them. To find failures, use the message class or the Logging Category; they differ:

- `@evt.name:Failed-Attempt`: the individual failed authentications and authorizations (for example `5400`, `5401`, `5402`, `5411`). Use it to count failed logins.
- `@cisco_ise.category:Failed_Attempts`: everything in ISE's *Failed Attempts* category, which also includes summaries of repeated failures (`5434`, `5449`), failed CoA requests (`5417`), and failed guest logins (`5418`).

The message code (`@cisco_ise.message_code`) selects one message type. Common codes:

| Code | Message |
|---|---|
| `5200` / `5400` | RADIUS authentication succeeded / failed |
| `5411` | Supplicant stopped responding to ISE (for example, a wrong PEAP password) |
| `5434` / `5449` | Repeated failures of the same endpoint (`cisco_ise.attributes.TotalFailedAttempts`) / endpoint rejected |
| `5201` / `5401` | TACACS+ authentication succeeded / failed |
| `5202` / `5402` | TACACS+ command authorization succeeded / failed |
| `3300` | TACACS+ command accounting (the command typed) |
| `3000` / `3002` / `3001` | RADIUS accounting start / interim update / stop |

The full list is in Cisco's [Cisco ISE Syslogs][10] guide.

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

**Fields are missing, or many logs have only the header parsed:**

ISE splits an event longer than the Remote Logging Target's **Maximum Length** into several syslog messages, and only the first one is parsed. To find the other parts, search for `source:cisco-ise -@cisco_ise.segment.number:0`. Set **Maximum Length** to 8192, or to the highest value your ISE version accepts.

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
[10]: https://www.cisco.com/c/en/us/td/docs/security/ise/syslog/Cisco_ISE_Syslogs/m_SyslogsList.html
