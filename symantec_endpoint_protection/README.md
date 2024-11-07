## Overview

[Symantec Endpoint Protection][5] is a client-server solution that protects laptops, desktops, and servers in your network against malware, risks, and vulnerabilities. Symantec Endpoint Protection combines virus protection with advanced threat protection to proactively secure your client computers against known and unknown threats, such as viruses, worms, Trojan horses, and adware. Symantec Endpoint Protection provides protection against even the most sophisticated attacks that evade traditional security measures, such as rootkits, zero-day attacks, and spyware that mutates.

This integration enriches and ingests the following logs from Symantec Endpoint Protection:

- **Audit logs**: Record changes to policies such as policy updates, policy assignments, and more.
- **Risk logs**: Track and record potential security risks detected on endpoints, including malware, vulnerabilities, and suspicious activities.
- **Scan logs**: Record the results of antivirus scans, including detected malware, scan settings, and user information.
- **System logs**: Record all administrative activities, client activities, server activities and `client_server` activities.
- **Security logs**: Record security-related events, including attacks, compliance, and device control.
- **Application control logs**: Record events related to application control, such as blocked or allowed applications.
- **Traffic logs**: Record network traffic events, including incoming and outgoing connections, protocols, and ports.

You can also visualize detailed insights into the above-mentioned logs with the out-of-the-box dashboards. Once you've installed the integration, you can find the dashboards by searching for "symantec-endpoint-protection" in the dashboards list.

## Setup

### Installation

To install the Symantec Endpoint Protection integration, run the following Agent installation command and the steps below. For more information, see the [Integration Management documentation][6].

**Note**: This step is not necessary for Agent version >= 7.52.0.

Linux command:

  ```shell
  sudo -u dd-agent -- datadog-agent integration install datadog-symantec_endpoint_protection==1.0.0
  ```

### Configuration

#### Log collection

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in `datadog.yaml`:

    ```yaml
    logs_enabled: true
    ```

2. Add this configuration block to your `symantec_endpoint_protection.d/conf.yaml` file to start collecting your Symantec Endpoint Protection logs.

    See the [sample symantec_endpoint_protection.d/conf.yaml][6] for available configuration options.

      ```yaml
      logs:
       - type: udp
         port: <PORT>
         service: symantec-endpoint-protection
         source: symantec-endpoint-protection
      ```

3. [Restart the Agent][1].

4. Configure Syslog Message Forwarding from Symantec Endpoint Protection Server:

    1. Log on to your **Symantec Endpoint Protection Server**.
    2. Click on **Admin**.
    3. Click on **servers** on the **administrative** panel.
    4. Select **sites** for which you want to forward logs.
    5. Click on **Configure external logging**.
    6. Enable Transmission of Logs to a Syslog Server.
    7. Provide your **syslog server IP**.
    8. Select network protocol as **UDP**.
    9. Provide the **PORT** where you want to forward logs.

### Validation

[Run the Agent's status subcommand][2] and look for `symantec_endpoint_protection` under the Checks section.

## Data Collected

### Logs

The Symantec Endpoint Protection integration collects audit, risk, scan, security, traffic, application control, and system logs.

### Metrics

The Symantec Endpoint Protection integration does not include any metrics.

### Events

The Symantec Endpoint Protection integration does not include any events.

### Service Checks

The Symantec Endpoint Protection integration does not include any service checks.

## Troubleshooting

### Permission denied while port binding

If you see a **Permission denied** error while port binding in the Agent logs, see the following instructions:

   1. Binding to a port number under 1024 requires elevated permissions. Grant access to the port using the `setcap` command:

      - Grant access to the port using the `setcap` command:

         ```shell
         sudo setcap CAP_NET_BIND_SERVICE=+ep /opt/datadog-agent/bin/agent/agent
         ```

      - Verify the setup is correct by running the `getcap` command:

         ```shell
         sudo getcap /opt/datadog-agent/bin/agent/agent
         ```

         With the expected output:

         ```shell
         /opt/datadog-agent/bin/agent/agent = cap_net_bind_service+ep
         ```

         **Note**: Re-run this `setcap` command every time you upgrade the Agent.

   2. [Restart the Agent][1].

### Data is not being collected

Make sure that traffic is bypassed from the configured port if the firewall is enabled.

### Port already in use

If you see the **Port <PORT-NO\> Already in Use** error, see the following instructions. The example below is for PORT-NO = 514:

On systems using Syslog, if the Agent listens for Cisco Secure Firewall logs on port 514, the following error can appear in the Agent logs: `Can't start UDP forwarder on port 514: listen udp :514: bind: address already in use`.

This error occurs because by default, Syslog listens on port 514. To resolve this error, take **one** of the following steps:

- Disable Syslog.
- Configure the Agent to listen on a different, available port.

Need help? Contact [Datadog support][3].

[1]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[3]: https://docs.datadoghq.com/help/
[4]: https://docs.datadoghq.com/agent/
[5]: https://techdocs.broadcom.com/us/en/symantec-security-software/endpoint-security-and-management/endpoint-protection/all/what-is-v45096464-d43e1648.html
[6]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install