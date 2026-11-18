## Overview

[Cisco Identity Services Engine (ISE)][4] is a network access control platform. It decides whether users and devices may join the wired, wireless, or VPN network and with which access (VLAN, downloadable ACL, Security Group Tag), and it authenticates network administrators on switches and routers through TACACS+.

Integrate Cisco ISE with Datadog to search and analyze ISE's syslog messages: RADIUS authentications and failures with the user, endpoint MAC address, network device, port, SSID, and site; RADIUS accounting, which links endpoint IP addresses to users and MAC addresses; TACACS+ logins and commands; ISE administrator logins and configuration changes; profiling; guest and My Devices portal activity. Datadog uses its built-in log pipeline to parse and enrich these logs into Datadog standard attributes and `cisco_ise.*` attributes. The logs can also be used by Cloud SIEM detection rules.

**Disclaimer**: Your use of this integration, which may collect data that includes personal information, is subject to your agreements with Datadog. Cisco is not responsible for the privacy, security or integrity of any end-user information, including personal data, transmitted through your use of the integration.

## Setup

Cisco ISE sends its logs as syslog to a **Remote Logging Target**. Point a target at a Datadog Agent that listens on a UDP or TCP port, and attach the Logging Categories you want to collect to it.

Supported versions: Cisco ISE 3.x (tested on 3.2).

### Configuration

#### Enable log collection on the Datadog Agent

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in `datadog.yaml`:

    ```yaml
    logs_enabled: true
    ```

2. Add this configuration block to your `cisco_ise.d/conf.yaml` file to start collecting your Cisco ISE logs:

    <!-- RFC Q3 (proposed answer): UDP by default, TCP across firewalls or a WAN. -->
    <!-- RFC Q1 (proposed answer): mask secrets typed in TACACS+ commands in the Agent. -->

    ```yaml
    logs:
      - type: udp # or tcp
        port: <PORT>
        source: cisco-ise
        service: cisco-ise
        log_processing_rules:
          - type: mask_sequences
            name: ise_tacacs_cmd_secret
            pattern: '(CmdAV=[^\]=]*?\b(?:secret|password|key|key-string|community|pre-shared-key)(?: [0-9])? )[^ \]<][^ \]]*'
            replace_placeholder: '${1}********'
          - type: mask_sequences
            name: ise_tacacs_cmdarg_secret
            pattern: '(CmdArgAV=(?:secret|password|key|key-string|community|pre-shared-key) (?:CmdArgAV=[0-9] )?CmdArgAV=)[^ <][^ ]*'
            replace_placeholder: '${1}********'
    ```

    See the sample [`cisco_ise.d/conf.yaml`][5] file for available configuration options. The two `mask_sequences` rules are explained in [Sensitive data](#sensitive-data).

    **Note**: Do not change the `source` value, as it is integral to the pipeline's operation.

3. [Restart the Agent][3].

**UDP or TCP**: both work with the same pipeline. UDP is the simplest, and ISE never waits for the Agent, but a lost packet loses the event silently, and 8192-byte messages are IP-fragmented, which some firewalls drop. Use TCP when firewalls or a WAN sit between ISE and the Agent. Over TCP, ISE ends each message with a newline, so the Agent's default `tcp` listener needs no extra settings; don't set an `idle_timeout` on it, because ISE keeps one long-lived and often quiet connection. TLS (ISE's "Secure Syslog" target) is not supported.

#### Configure a Remote Logging Target in Cisco ISE

1. In the ISE admin UI, go to **Administration** > **System** > **Logging** > **Remote Logging Targets** and click **Add**.
2. Set the following:
    - **Name**: for example, `datadog_agent` (names can't contain `-`).
    - **Target Type**: **UDP SysLog** or **TCP SysLog**, matching the Agent's `type`.
    - **Host / IP Address**: the IP address of the Datadog Agent host.
    - **Port**: the `port` set in `cisco_ise.d/conf.yaml`.
    - **Maximum Length**: **8192**. This is required, over UDP and TCP. With ISE's default of 1024, most events are split into 2 to 5 syslog messages; each one becomes a separate Datadog log and only the first one is parsed, so fields such as the identity group or the endpoint MAC address are missing.
    - For **TCP SysLog**, leave **Comply to RFC 3164** off. **Buffer Messages When Server Down** is optional.
3. Click **Save**.

#### Attach Logging Categories to the target

ISE only sends the categories attached to a target. Go to **Administration** > **System** > **Logging** > **Logging Categories**, and for each category below, select it, add the target to **Selected Targets**, and click **Save**:

| Logging Category | What it contains |
|---|---|
| Passed Authentications | RADIUS and TACACS+ authentications that succeeded, guest logins, dACL downloads |
| Failed Attempts | Failed authentications and authorizations, repeated failures (`5434`), failed CoA |
| RADIUS Accounting | Session start, interim update, and stop: the only place the endpoint IP address appears |
| TACACS Accounting | Commands typed on network devices through TACACS+ |
| Administrative and Operational Audit | ISE administrator logins and configuration changes |
| Profiler | Endpoint profiling results (device type, operating system, vendor) |
| Guest, MyDevices | Guest self-registration and the My Devices portal |
| Posture and Client Provisioning Audit | Posture results and quarantine (ANC) actions |

#### Recommended network device and ISE settings

- **RADIUS accounting, including interim updates, on the switches and wireless controllers.** The endpoint IP address is only reported after DHCP, in accounting messages, so the IP address to user and MAC address mapping depends on it.
- **Network device Location groups** (**Administration** > **Network Resources** > **Network Device Groups**). The device's location path, such as `All Locations#Spain#Madrid`, is the site in the logs, split into `cisco_ise.site.level1` to `level5` (without the `All Locations` root).
- Leave ISE's suppression of repeated events on (the default) to avoid most repeated re-authentications.

#### Optional: drop noisy messages in the Agent

ISE logs some messages that rarely matter, such as `52000` configuration changes for `DockerMetrics`, `61025` and `61026` on every EAP-TLS login, and `60188` on every normal SSH logout. The pipeline parses them; to stop sending them, add an `exclude_at_match` rule to the logs configuration, for example:

```yaml
        log_processing_rules:
          - type: exclude_at_match
            name: ise_exclude_docker_metrics
            pattern: 'ObjectType=DockerMetrics'
```

### Validation

[Run the Agent's status subcommand][2] and look for `cisco_ise` under the Logs Agent section. In the [Log Explorer][6], search for `source:cisco-ise`.

## Data Collected

### Logs

The Cisco ISE integration collects ISE's syslog messages and parses them with the `cisco-ise` log pipeline:

- The syslog header gives the ISE node (`syslog.hostname`, also copied to `cisco_ise.node`), the Logging Category (`cisco_ise.category`), and the message ID and segment numbers.
- The message body gives the event time with milliseconds, the message code (`cisco_ise.message_code`, for example `5200` for a passed authentication), the severity (the log status), and ISE's own fields.
<!-- RFC Q2 (proposed answer): ISE key names kept under cisco_ise.attributes.*, site split into cisco_ise.site.level1..5 (RFC v11). -->
- ISE's fields keep their names under `cisco_ise.attributes.*` (for example `cisco_ise.attributes.NetworkDeviceName`, `cisco_ise.attributes.FailureReason`), and the authorization result `Response={...}` is parsed under `cisco_ise.response.*`.
- Derived fields: the site levels, the normalized endpoint MAC address (`cisco_ise.endpoint.mac`), and the TACACS+ command (`cisco_ise.tacacs.command`, `cisco_ise.tacacs.command_name`).
- Standard attributes: `usr.name`, `network.client.ip`, and `evt.name` (ISE's message class, for example `Passed-Authentication` or `Failed-Attempt`).

ISE logs unknown users as `INVALID`, so failed logins by non-existing users are grouped under `usr.name:INVALID`.

#### Finding failed logins

<!-- RFC Q5 (proposed answer): no evt.outcome; the pipeline keeps ISE code, category, and class as sent. -->

ISE has no single success or failure field, so the pipeline keeps the values ISE sends and doesn't classify them. To find failures, use the Logging Category (`@cisco_ise.category:Failed_Attempts`), the message class (`@evt.name:Failed-Attempt`), or the message code. Common codes:

| Code | Message |
|---|---|
| `5200` / `5400` | RADIUS authentication succeeded / failed |
| `5411` | Supplicant stopped responding to ISE (for example, a wrong PEAP password) |
| `5434` / `5449` | Repeated failures of the same endpoint (`cisco_ise.attributes.TotalFailedAttempts`) / endpoint rejected |
| `5201` / `5401` | TACACS+ authentication succeeded / failed |
| `5202` / `5402` | TACACS+ command authorization succeeded / failed |
| `3300` | TACACS+ command accounting (the command typed) |
| `3000` / `3002` / `3001` | RADIUS accounting start / interim update / stop |

The full list is in Cisco's [Cisco ISE Syslogs][8] guide.

#### Sensitive data

<!-- RFC Q1 (proposed answer): mask TACACS+ secrets in the Agent, keep guest data, mention Sensitive Data Scanner. -->

- **TACACS+ commands** are logged as typed, including secrets, for example `username admin secret 0 <password>`. The two `mask_sequences` rules in the configuration above replace the value after `secret`, `password`, `key`, `key-string`, `community`, and `pre-shared-key` with `********` in the Agent, before the logs leave your network. They only cover these keywords; to mask other values, add rules or use [Sensitive Data Scanner][7].
- **Guest portal messages** (Guest category, and guest logins) contain visitors' personal data: name, email address, phone number, company, and the person visited. Don't attach the Guest category if you don't need it, or use [Sensitive Data Scanner][7] to redact these fields.

### Metrics

Cisco ISE does not include any metrics.

### Events

The Cisco ISE integration does not include any events.

## Troubleshooting

**Fields are missing, or many logs have only the header parsed:**

The Remote Logging Target's **Maximum Length** is lower than 8192. ISE splits longer events into several syslog messages (`@cisco_ise.segment.number:>0`), and only the first one is parsed. Set **Maximum Length** to 8192.

**Permission denied while port binding:**

Binding to a port number under 1024 requires elevated permissions. Grant access to the port using the `setcap` command, then [restart the Agent][3]:

```shell
sudo setcap CAP_NET_BIND_SERVICE=+ep /opt/datadog-agent/bin/agent/agent
```

Re-run this command every time you upgrade the Agent.

**Data is not being collected:**

Make sure that the firewall on the Agent host allows traffic to the configured port, and that the ISE target is enabled and attached to the Logging Categories.

**Port already in use:**

On systems running syslog, port 514 is usually taken. Configure the Agent to listen on a different, available port and use the same port in the ISE target.

Need help? Contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[3]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[4]: https://www.cisco.com/site/us/en/products/security/identity-services-engine/index.html
[5]: https://github.com/DataDog/integrations-core/blob/master/cisco_ise/datadog_checks/cisco_ise/data/conf.yaml.example
[6]: https://app.datadoghq.com/logs?query=source%3Acisco-ise
[7]: https://docs.datadoghq.com/security/sensitive_data_scanner/
[8]: https://www.cisco.com/c/en/us/td/docs/security/ise/syslog/Cisco_ISE_Syslogs/m_SyslogsList.html
