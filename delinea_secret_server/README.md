## Overview

[Delinea Secret Server][4] is an enterprise-grade password management solution designed to help organizations securely store, manage, and control access to privileged credentials. It aims to improve the security of sensitive data, reduce the risk of data breaches, and streamline the password management process.

This integration enriches and ingests the following logs:

- **Secret Server Logs**: Represents an event where a user performs an action (such as viewing, adding, or modifying) on a stored secret, folder, group, or user. It provides details including the user's identity, the source of the action, and the  item the action was performed.

After it collects the logs, Delinea Secret Server channels them into Datadog for analysis. Using the built-in logs pipeline, these logs are parsed and enriched, allowing for effortless search and analysis. The integration provides insights into secret server logs through out-of-the-box dashboards and includes ready-to-use Cloud SIEM detection rules for improved monitoring and security.

**Minimum Agent version:** 7.67.0

## Setup

### Installation

To install the Delinea Secret Server integration, run the following Agent installation command and the following steps. For more information, see the [Integration Management][5] documentation.

**Note**: This step is not necessary for Agent version >= 7.65.0.

Linux command:

  ```shell
  sudo -u dd-agent -- datadog-agent integration install datadog-delinea-secret-server==1.0.0
  ```

### Configuration

#### Log collection

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in the `datadog.yaml` file:

    ```yaml
    logs_enabled: true
    ```

2. Add this configuration block to your `delinea_secret_server.d/conf.yaml` file to start collecting your Delinea Secret Server logs.

   ```yaml
      logs:
       - type: tcp/udp
         port: <PORT>
         source: delinea-secret-server
         service: delinea-secret-server
      ```

      For available configuration options, see the [sample delinea_secret_server.d/conf.yaml][7]. Choose the appropriate protocol (either TCP or UDP) based on your Delinea Secret Server syslog forwarding configuration.

      **Note**: Do not change the service and source values, as these parameters are integral to the pipeline's operation.

3. [Restart the Agent][1].

#### Configure syslog message forwarding from Delinea Secret Server

1. Log in to the **Delinea Secret Server** platform.
2. Navigate to **Settings** > **All Settings**.
3. Navigate to **Configuration** > **General** > **Application**.
4. Click **Edit**.
5. Check **Enable Syslog/CEF Log Output**.
6. Fill out the following information:

    - **Syslog/CEF Server**: Enter Syslog/CEF Server Address.
    - **Syslog/CEF Port**: Enter Syslog/CEF Server Port.
    - **Syslog/CEF Protocol**: Select TCP or UDP.
    - **Syslog/CEF Time Zone**: Select UTC Time.
    - **Syslog/CEF DateTime Format**: Select ISO 8601.
    - **Syslog/CEF Site**: Select the site that the CEF/Syslogs will run on.

7. Click **Save**.

### Validation

[Run the Agent's status subcommand][2] and look for `delinea_secret_server` under the Checks section.

## Data Collected

### Logs

The Delinea Secret Server integration collects Secret Server Logs.

### Metrics

The Delinea Secret Server integration does not include any metrics.

### Events

The Delinea Secret Server integration does not include any events.

### Service Checks

The Delinea Secret Server integration does not include any service checks.

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

On systems using Syslog, if the Agent listens for Delinea Secret Server logs on port 514, the following error can appear in the Agent logs: `Can't start UDP forwarder on port 514: listen udp :514: bind: address already in use`.

By default, Syslog listens on port 514. To resolve this error, take **one** of the following steps:

- Disable Syslog.
- Configure the Agent to listen on a different, available port.

Need help? Contact [Datadog support][3].

[1]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[3]: https://docs.datadoghq.com/help/
[4]: https://delinea.com/products/secret-server
[5]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install
[6]: https://docs.delinea.com/online-help/secret-server/start.htm
[7]: https://github.com/DataDog/integrations-core/blob/master/delinea_secret_server/datadog_checks/delinea_secret_server/data/conf.yaml.example