# Agent Integration: Cisco ISE

## Overview

This integration collects [Cisco Identity Services Engine (ISE)][4] logs through the Datadog Agent.

Cisco ISE is a network access control platform. It decides whether users and devices may join the wired, wireless, or VPN network and with which access (VLAN, downloadable ACL, Security Group Tag), and it authenticates network administrators on switches and routers through TACACS+. ISE sends its logs as syslog to a **Remote Logging Target**; this integration points that target at a Datadog Agent that listens on a UDP or TCP port.

### What this integration monitors

The integration collects ISE's logs for each kind of activity ISE controls:

- **Network access (RADIUS authentications)**: Who joined the network or failed to, with the user, the endpoint MAC address, the network device and port, the SSID, the site, the authentication method, the authorization result (VLAN, downloadable ACL, Security Group Tag), and the failure reason.
- **Network sessions (RADIUS accounting)**: Session start, interim updates, and stop. They link each endpoint IP address to its user and MAC address.
- **Device administration (TACACS+)**: Administrator logins on switches and routers, their privilege level, and the commands they type.
- **ISE administration**: ISE administrator logins and configuration changes.
- **Endpoint profiling**: The device type, operating system, and vendor ISE assigns to each endpoint.
- **Guest and My Devices portals**: Guest self-registration and logins, and the devices employees register.
- **Posture and quarantine**: Posture results and quarantine (Adaptive Network Control) actions.

### Supported versions

Cisco ISE 3.x (tested on 3.2).

## Setup

### Installation

The Cisco ISE integration is included in the [Datadog Agent][8] package. No additional installation is needed on the Agent host, and nothing is installed on ISE: ISE pushes its logs to the Agent, which must be reachable from the ISE nodes on the port you configure.

### Configuration

Configure the Agent to listen on a UDP or TCP port, then point an ISE Remote Logging Target at it and attach the Logging Categories to collect.

#### Configure the Datadog Agent

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in `datadog.yaml`:

    ```yaml
    logs_enabled: true
    ```

2. Add this configuration block to your `cisco_ise.d/conf.yaml` file to start collecting your Cisco ISE logs:

    ```yaml
    logs:
      - type: udp # or tcp
        port: <PORT>
        source: cisco-ise
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

**UDP or TCP**: both are supported; choose the one that fits your network. Over UDP, ISE never waits for the Agent, but a lost packet loses the event silently, and 8192-byte messages are IP-fragmented, which some firewalls drop. Over TCP, nothing is lost silently, and ISE ends each message with a newline, so the Agent's default `tcp` listener needs no extra settings; don't set an `idle_timeout` on it, because ISE keeps one long-lived and often quiet connection. TLS (ISE's "Secure Syslog" target) is not supported.

#### Configure a Remote Logging Target in Cisco ISE

1. In the ISE admin UI, go to **Administration** > **System** > **Logging** > **Remote Logging Targets** and click **Add**.
2. Set the following:
    - **Name**: for example, `datadog_agent` (names can't contain `-`).
    - **Target Type**: **UDP SysLog** or **TCP SysLog**, matching the Agent's `type`.
    - **Host / IP Address**: the IP address of the Datadog Agent host.
    - **Port**: the `port` set in `cisco_ise.d/conf.yaml`.
    - **Maximum Length**: **8192**. This is required, over UDP and TCP. With ISE's default of 1024, most events are split into 2 to 5 syslog messages; each one becomes a separate Datadog log, so the fields of one event, such as the identity group or the endpoint MAC address, are spread over several logs.
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
- **Network device Location groups** (**Administration** > **Network Resources** > **Network Device Groups**). The device's location path, such as `All Locations#Spain#Madrid`, is the site in the logs.
- Leave ISE's suppression of repeated events on (the default) to avoid most repeated re-authentications.

#### Optional: drop noisy messages in the Agent

ISE logs some messages that rarely matter, such as `52000` configuration changes for `DockerMetrics`, `61025` and `61026` on every EAP-TLS login, and `60188` on every normal SSH logout. To stop sending them, add an `exclude_at_match` rule to the logs configuration, for example:

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

The Cisco ISE integration collects ISE's syslog messages with `source:cisco-ise`, for the activity listed in [What this integration monitors](#what-this-integration-monitors).

#### Sensitive data

- **TACACS+ commands** are logged as typed, including secrets, for example `username admin secret 0 <password>`. The two `mask_sequences` rules in the configuration above replace the value after `secret`, `password`, `key`, `key-string`, `community`, and `pre-shared-key` with `********` in the Agent, before the logs leave your network. They only cover these keywords; to mask other values, add rules or use [Sensitive Data Scanner][7].
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

The Remote Logging Target's **Maximum Length** is lower than 8192. ISE splits longer events into several syslog messages, and each one becomes a separate log. Set **Maximum Length** to 8192.

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
