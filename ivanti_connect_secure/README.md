## Overview

[Ivanti Connect Secure][3] gives employees, partners and customers secure and controlled access to corporate data and applications. The applications include file servers, web servers, native messaging, and hosted servers outside your trusted network.

This integration parses the following types of logs:

- **Web Requests** : Logs provide information about client requests to web-based resources, including successful, failed, blocked, denied, and unauthenticated requests.
- **Authentication** : Logs provide information about login-related events, SSL negotiation failures, and remote address change events.
- **Connection** : Logs provide information about connections, including details on bytes transferred, duration, hostname, and IP addresses.
- **VPN Tunneling** : Logs provide information about ACL-related activity, as well as VPN session related events.
- **Statistics** : Logs provide information into system usage, including concurrent users, and other performance metrics.
- **Administrator Activities** : Logs provide information on actions performed by administrators, such as logins, configuration changes, and system management tasks.

Visualize detailed insights into these logs through the out-of-the-box dashboards. Additionally, ready-to-use Cloud SIEM detection rules are available to help you monitor and respond to potential security threats effectively.

## Setup

### Installation

To install the Ivanti Connect Secure integration, run the following Agent installation command in your terminal, then complete the configuration steps below. For more information, see the [Integration Management][4] documentation.

**Note**: This step is not necessary for Agent version >= 7.59.0.

```shell
sudo -u dd-agent -- datadog-agent integration install datadog-ivanti_connect_secure==1.0.0
```

### Configuration

#### Log collection

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in `datadog.yaml`:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `ivanti_connect_secure.d/conf.yaml` file to start collecting your logs.

   See the sample [ivanti_connect_secure.d/conf.yaml][6] for available configuration options.

   ```yaml
   logs:
     - type: tcp # or 'udp'
       port: <PORT>
       source: ivanti-connect-secure
       service: ivanti-connect-secure
   ```

   **Note**:

   - `PORT`: Port should be similar to the port provided in **Configure syslog message forwarding from Ivanti Connect Secure** section.
   - It is recommended not to change the service and source values, as these parameters are integral to the pipeline's operation.

3. [Restart the Agent][2].

#### Configure syslog message forwarding from Ivanti Connect Secure

1. Login in to the Ivanti Connect Secure Admin Portal.
2. Navigate to **System** > **Log/Monitoring** > **Events**.
3. Click the **Settings** tab.
4. Under **Select Events to Log**, ensure all event types are selected.
5. Click **Save Changes** to apply the configuration.
6. Configure the syslog server details in the **Syslog Servers** section:
   - **Server name/IP**: Enter the fully qualified domain name or IP address of the syslog server in the format `<IP/DOMAIN>:<PORT>`.
   - **Type**: Select either **TCP** or **UDP** from the dropdown.
   - **Filter**: Choose **JSON: JSON** from the dropdown.
     <br>After entering the required details, click **Add**.
7. Repeat steps 3 to 6 in the **User Access** and **Admin Access** tabs.

### Validation

[Run the Agent's status subcommand][5] and look for `ivanti_connect_secure` under the Checks section.

## Data Collected

### Log

| Format | Event Types                                                                                   |
| ------ | --------------------------------------------------------------------------------------------- |
| JSON   | Web Requests, Authentication, Connection, VPN Tunneling, Statistics, Administrator Activities |

### Metrics

The Ivanti Connect Secure integration does not include any metrics.

### Events

The Ivanti Connect Secure integration does not include any events.

### Service Checks

The Ivanti Connect Secure integration does not include any service checks.

## Troubleshooting

**Permission denied while port binding:**

If you see a **Permission denied** error while port binding in the Agent logs:

1. Binding to a port number under 1024 requires elevated permissions. Grant access to the port using the `setcap` command:

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

3. [Restart the Agent][2].

**Data is not being collected:**

Ensure traffic is bypassed from the configured port if the firewall is enabled.

**Port already in use:**

If you see the **Port <PORT_NUMBER> Already in Use** error, see the following instructions. The following example is for port 514:

- On systems using Syslog, if the Agent listens for events on port 514, the following error can appear in the Agent logs: `Can't start UDP forwarder on port 514: listen udp :514: bind: address already in use`. This error occurs because by default, Syslog listens on port 514. To resolve this error, take **one** of the following steps:
  - Disable Syslog.
  - Configure the Agent to listen on a different, available port.

For further assistance, contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[3]: https://www.ivanti.com/products/connect-secure-vpn
[4]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/ivanti_connect_secure/datadog_checks/ivanti_connect_secure/data/conf.yaml.example
