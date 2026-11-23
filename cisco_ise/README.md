# Agent Integration: Cisco ISE

## Overview

This integration collects [Cisco Identity Services Engine (ISE)][4] logs through the Datadog Agent.

Cisco ISE is a network access control platform. It decides whether users and devices may join the wired, wireless, or VPN network and with which access (VLAN, downloadable ACL, Security Group Tag), and it authenticates network administrators on switches and routers through TACACS+. ISE sends its logs as syslog to a **Remote Logging Target**; this integration points that target at a Datadog Agent that listens on a UDP or TCP port.

### What this integration monitors

The integration collects ISE's logs for each kind of activity ISE controls:

- **Network access (RADIUS authentications)**, Logging Categories *Passed Authentications* and *Failed Attempts*: Who joined the network or failed to, with the user, the endpoint MAC address, the network device and port, the SSID, the site, the authentication method, the authorization result (VLAN, downloadable ACL, Security Group Tag), and the failure reason.
- **Network sessions (RADIUS accounting)**, *RADIUS Accounting*: Session start, interim updates, and stop. They link each endpoint IP address to its user and MAC address.
- **Device administration (TACACS+)**, logins in *Passed Authentications* and *Failed Attempts*, commands in *TACACS Accounting*: Administrator logins on switches and routers, their privilege level, and the commands they type.
- **ISE administration**, *Administrative and Operational Audit*: ISE administrator logins and configuration changes.
- **Endpoint profiling**, *Profiler*: The device type, operating system, and vendor ISE assigns to each endpoint.
- **Guest and My Devices portals**, *Guest* and *MyDevices*: Guest self-registration and logins, and the devices employees register.
- **Posture and quarantine**, *Posture and Client Provisioning Audit*: Posture results and quarantine (Adaptive Network Control) actions.

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

2. Edit the `cisco_ise.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory. Start from the sample [cisco_ise.d/conf.yaml][5]: uncomment the `logs` section and set the port. Both UDP and TCP are supported (`type: udp` or `type: tcp`); TLS is not.

    ```yaml
    logs:
      - type: udp
        port: <PORT>
        source: cisco-ise
    ```

    Keep the two `log_processing_rules` that follow in the sample: they mask secrets typed in TACACS+ commands (see [Sensitive data](#sensitive-data)). Do not change the `source` value, as it is integral to the pipeline's operation.

3. [Restart the Agent][3].

#### Configure Cisco ISE

In Cisco ISE, add a Remote Logging Target for the Agent: UDP or TCP syslog (matching the Agent's `type`), the Agent host, and the port set above. Set its **Maximum Length** to **8192**: this is required, over UDP and TCP. With ISE's default of 1024, most events are split into several syslog messages, and each one becomes a separate log.

Then attach to the target the Logging Categories of the activity you want to collect, listed in [What this integration monitors](#what-this-integration-monitors). ISE only sends the categories attached to a target.

#### Recommended settings

- RADIUS accounting, including interim updates, on the network devices: the endpoint IP address is only reported in accounting messages.
- Location groups for the network devices in ISE: a device's location path is the site in the logs.
- ISE's suppression of repeated events left on (the default).

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

- **TACACS+ commands** are logged as typed, including secrets, for example `username admin secret 0 <password>`. The two `mask_sequences` rules in the sample configuration replace the value after `secret`, `password`, `key`, `key-string`, `community`, and `pre-shared-key` with `********` in the Agent, before the logs leave your network. They only cover these keywords; to mask other values, add rules or use [Sensitive Data Scanner][7].
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
