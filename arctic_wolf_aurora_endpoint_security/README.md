## Overview

[Arctic Wolf Aurora Endpoint Security][4] is a unified solution that helps to tackle modern threats. It provides comprehensive capabilities to detect and protect against threats across endpoints.

This integration enriches and ingests the following events:

- **Aurora Protect Desktop Events**: Log messages generated for application control, audit logs, devices, device control, memory protection, script control, threats and threat classification.
- **Aurora Focus Detection Events**: Malicious or suspicious events detected by Aurora Focus. The events includes security process and system events, network events and system tool events.

This integration collects all the above listed logs, channeling them into Datadog for analysis. Using the built-in logs pipeline, these logs are parsed and enriched, enabling search and analysis. The integration provides insight into desktop and detection events through out-of-the-box dashboards. Additionally, it includes ready-to-use Cloud SIEM detection rules for enhanced monitoring and security.

**Minimum Agent version**: 7.74.0

## Setup

### Configuration

#### Enable log collection

1. Collecting logs is disabled by default in the Datadog Agent. Enable log collection in `datadog.yaml`:

    ```yaml
    logs_enabled: true
    ```

2. Add the following configuration block to your `arctic_wolf_aurora_endpoint_security.d/conf.yaml` file to start collecting Arctic Wolf Aurora Endpoint Security logs.

      ```yaml
      logs:
       - type: tcp # or 'udp'
         port: <PORT>
         service: arctic-wolf-aurora-endpoint-security
         source: arctic-wolf-aurora-endpoint-security
      ```
      See the sample [`arctic_wolf_aurora_endpoint_security.d/conf.yaml`][6] file for available configuration options.

      Note:
      - PORT: Port should be similar to the port provided in **Configuration needed on Arctic Wolf Aurora Endpoint Security**.
      - We recommend you do not change the service and source values, as these parameters are integral to the pipeline's operation.

3. [Restart the Agent][1].

#### Configure Arctic Wolf Aurora Endpoint Security settings

1. Log in to Arctic Wolf Aurora Endpoint Security platform.
2. In the management console, on the menu bar, go to **Settings** > **Application**.
3. Enable the **Syslog/SIEM** option.
4. Enable the following event types to be sent to the syslog server:
   - Application Control
   - Audit Log
   - Devices
   - Device Control
   - Optics Events
   - Memory Protection
   - Script Control
   - Threats
   - Threat Classifications
   - Network Threats
5. Set the **SIEM** field to **Other**.
6. Set the **Protocol** field to **TCP/UDP**.
7. Enable the **Allow messages over 2 KB** option.
8. In the **IP/Domain** field, enter the public **IP address** of the Datadog Agent that will receive the logs.
9. In the **Port** field, specify an open **port** on the Datadog Agent for receiving logs.
10. Set the **Severity** level to **Debug (7)**.
11. Set the **Facility** value to **Local0 (16)**.
12. In **Include tenant identifiers**, specify whether the tenant ID, name, or both should be included in the syslog messages.
13. Click **Save**.

**Note**: The `Port` value should be similar to the port provided in the Log Collection section.


### Validation

[Run the Agent's status subcommand][2] and look for `arctic_wolf_aurora_endpoint_security` under the `Logs Agent` section.

## Data Collected

### Logs

The Arctic Wolf Aurora Endpoint Security integration collects `Aurora Protect Desktop` and `Aurora Focus Detection` Events.

### Metrics

The Arctic Wolf Aurora Endpoint Security integration does not include any metrics.

### Events

The Arctic Wolf Aurora Endpoint Security integration does not include any events.

## Troubleshooting

**Permission denied while port binding:**

If you see a **Permission denied** error while port binding in the Agent logs, see the following instructions:

   1. Binding to a port number under 1024 requires elevated permissions. Grant access to the port using the `setcap` command:

      1. Grant access to the port using the `setcap` command:

         ```shell
         sudo setcap CAP_NET_BIND_SERVICE=+ep /opt/datadog-agent/bin/agent/agent
         ```

      2. Verify the setup is correct by running the `getcap` command:

         ```shell
         sudo getcap /opt/datadog-agent/bin/agent/agent
         ```

         With the expected output:

         ```shell
         /opt/datadog-agent/bin/agent/agent = cap_net_bind_service+ep
         ```

         **Note**: Re-run this `setcap` command every time you upgrade the Agent.

   2. [Restart the Agent][1].

**Data is not being collected:**

Make sure that traffic is bypassed from the configured port if the firewall is enabled.

**Port already in use:**

If you see the **Port <PORT-NO\> Already in Use** error, see the following instructions. The example below is for `PORT-NO = 514`.

On systems using syslog, if the Agent listens for events on port 514, the following error can appear in the Agent logs: `Can't start UDP forwarder on port 514: listen udp :514: bind: address already in use`.

This error occurs because by default, Syslog listens on port 514. To resolve this error, take **one** of the following steps:

- Disable Syslog, or
- Configure the Agent to listen on a different, available port.

For any further assistance, contact [Datadog support][3].

[1]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[3]: https://docs.datadoghq.com/help/
[4]: https://docs.arcticwolf.com/bundle/AES-Overview/page/What-is-Aurora-Endpoint-Security.html
[5]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install
[6]: https://github.com/DataDog/integrations-core/blob/master/arctic_wolf_aurora_endpoint_security/datadog_checks/arctic_wolf_aurora_endpoint_security/data/conf.yaml.example