# Trend Micro Cloud One

## Overview

[Trend Micro Cloud One][1] is a cloud-native security platform designed to protect multi-cloud and hybrid environments such as AWS, Azure, and Google Cloud. It provides unified protection across workloads, files, and networks, all managed from a single console.

Integrate Trend Micro Cloud One with Datadog to gain insights into endpoint and workload security, file storage security, and network security events using pre-built dashboard visualizations. Datadog uses its built-in log pipelines to parse and enrich these logs, facilitating easy search and detailed insights. Additionally, integration includes ready-to-use Cloud SIEM detection rules for enhanced monitoring and security.

**Minimum Agent version:** 7.69.2

## Setup

### Log Collection Overview

**Note**: To collect all log types, you must configure both log collection methods.

The following table shows the log collection methods, the logs collected, and the dashboards populated for each method.

| Log Collection Method | Logs Collected | Dashboards Populated |
|-----------------------------------------|---------------------------------------------------------------------------|------------------------------|
| [Agent and Event Forwarder Configuration][8] | **Workload Security**  <br>- System Events  <br>- Anti-Malware Events  <br>- Application Control Events  <br>- Firewall Events  <br>- Integrity Monitoring Events  <br>- Intrusion Prevention Events  <br>- Log Inspection Events  <br>- Device Control Events  <br><br>**Network Security**  <br>- Reputation Events  <br>- IPS Events | - Trend Micro Cloud One - Workload Security Insights  <br>- Trend Micro Cloud One - System Events  <br>- Trend Micro Cloud One - Anti-Malware Events  <br>- Trend Micro Cloud One - Application Control and Device Control Events  <br>- Trend Micro Cloud One - Firewall Events  <br>- Trend Micro Cloud One - Integrity Monitoring Log Events  <br>- Trend Micro Cloud One - Intrusion Prevention Events  <br>- Trend Micro Cloud One - Log Inspection and Web Reputation Events  <br>- Trend Micro Cloud One - Network Security Insights |
| [File Storage Security API Configuration][9] | - File Storage Security Events | - Trend Micro Cloud One - File Storage Security Insights |

### Agent and Event Forwarder Configuration
****
#### Installation

To install the Trend Micro Cloud One integration, run the following Agent installation command in your terminal, then complete the configuration steps. For more information, see the [Integration Management][3] documentation.

**Note**: This step is not necessary for Agent version >= 7.71.0.

```shell
sudo -u dd-agent -- datadog-agent integration install datadog-trend_micro_cloud_one==1.0.0
```

#### Log collection

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in `datadog.yaml`:

   ```yaml
   logs_enabled: true
   ```

2. To collect logs, add the following configuration block to your `trend_micro_cloud_one.d/conf.yaml` file:

   See the sample [trend_micro_cloud_one.d/conf.yaml][7] for available configuration options.

   ```yaml
   logs:
     - type: udp
       port: <UDP-PORT>
       source: trend-micro-cloud-one
       service: workload-security
     - type: tcp
       port: <TCP-PORT>
       source: trend-micro-cloud-one
       service: network-security
   ```

   **Notes**:

   - `UDP-PORT`: Specify the publicly accessible UDP port that Datadog will listen on. This port is referenced later in the **Configure syslog message forwarding from Workload Security** section.
   - `TCP-PORT`: Specify the TCP port that Datadog will listen on. This port is referenced later in the **Configure syslog message forwarding from Network Security** section.
   - It is recommended to keep the default service and source values, as they are essential to the pipeline's functionality.

3. [Restart the Agent][5].

#### Configure syslog message forwarding from Workload Security

1. Log in to [Trend Micro Cloud One][1] and select **Endpoint & Workload Security**.
2. Go to **Policies** > **Common Objects** > **Other** > **Syslog Configurations**.
3. Click **New** > **New Configuration** > **General** and specify the following:
   - **Name**: Unique name that identifies the configuration.
   - **Server Name**: Datadog Agent's IP address.
   - **Server Port**: The `UDP-PORT` configured in [Log Collection][10].
   - **Transport**: Select UDP.
   - **Event Format**: Select Log Event Extended Format 2.0.
   - Enable Include time zone in events.
   - **Facility**: Select `Local 0`.
4. Click **OK**.
5. Forward System events:
   - i. Go to **Administration** > **System Settings** > **Event Forwarding**.
   - ii. From Forward System Events to a remote computer (via Syslog) using configuration, select an existing configuration from dropdown.
   - iii. Click **Save**.
6. Forward Security events:
   - i. Go to **Policies**.
   - ii. Double-click the policy whose events you want to push to Datadog.
   - iii. Go to **Settings** > **Event Forwarding**.
   - iv. Under Event Forwarding Frequency (from the Agent/Appliance), use Period between sending of events to select how often the security events are forwarded.
   - v. Under Event Forwarding Configuration (from the Agent/Appliance), use Anti-Malware Syslog Configuration and other protection modules' lists and select an existing Syslog configuration.
   - vi. Click **Save**.
   - vii. Repeat steps **ii** to **vi** for each base policy you want to push to Datadog.

#### Configure syslog message forwarding from Network Security

1. Log in to [Trend Micro Cloud One][1] Platform.
2. On the upper-right corner of the page, select the account for which you want to add an API key.
3. In the Dropdown, select **Account Settings**.
4. Navigate to **API Keys**.
5. Click New. In the New API Key section, provide the following details:
   - **API Key Alias**: Enter a descriptive name.
   - **Role**: Select `Full Access` from the dropdown.
   - **Language**: Select `English` from the dropdown.
   - **Timezone**: Select `UTC` from the dropdown.
6. Click **Next** and Copy **API Key**.
7. Navigate to the **Account Settings** section and copy the **Region**.
8. Make a curl request. Use the template below, putting values into the following fields:
   - **\<region>**: Region you copied in step 7.
   - **\<api-key>**: API Key you copied in step 6.
   - **\<appliances-id>**: ID of Appliance whose events you want pushed to Datadog.
   - **\<ip-address>**: Datadog Agent's IP address.
   - **\<port>**: Same `TCP-PORT` configured in [Log Collection][10].

   ```bash
   curl -X POST -k "https://network.<region>.cloudone.trendmicro.com/api/appliances/<appliances-id>/remotesyslogs" --header "api-version: v1" --header "Content-Type: application/json" --header "Authorization: ApiKey <api-key>" --data "{\"host\": \"<ip-address>\", \"port\": <port>, \"enabled\": true}"
   ```

9. Repeat the above step for each appliance you want to push to Datadog.

#### Validation

[Run the Agent's status subcommand][4] and look for `trend_micro_cloud_one` under the Checks section.

### File Storage Security API Configuration

#### Generate API credentials in Trend Micro Cloud One

1. Log in to [Trend Micro Cloud One][1] Platform.
2. On the upper-right corner of the page, select the account for which you want to add an API key.
3. In the dropdown, select **Account Settings**.
4. Navigate to **API Keys**.
5. Click New. In the New API Key section, provide the following details:
   - **API Key Alias**: Enter a descriptive name.
   - **Role**: Select `Read Only` from the dropdown.
   - **Language**: Select `English` from the dropdown.
   - **Timezone**: Select `UTC` from the dropdown.
6. Click **Next** and Copy **API Key**.
7. Navigate to the **Account Setting** section and copy the **Region**.

#### Connect your Trend Micro Cloud One Account to Datadog

1.  Add the application user's Trend Micro Cloud One Region, and API Key.

    | Parameters | Description                                         |
    | ---------- | --------------------------------------------------- |
    | Region     | The Region of your Trend Micro Cloud One Account.   |
    | API Key    | The API Key for your Trend Micro Cloud One Account. |

2.  Click **Save**.

## Data Collected

### Logs

The Trend Micro Cloud One integration collects and forwards workload security, file storage security, and network security events to Datadog.

### Metrics

Trend Micro Cloud One integration does not include any metrics.

### Events

Trend Micro Cloud One integration does not include any events.

## Troubleshooting

### Permission denied while port binding

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

3. [Restart the Agent][5].

### Data is not being collected

Ensure firewall settings allow traffic through the configured port.

### Port already in use

On systems running Syslog, the Agent may fail to bind to port 514 and display the following error:

    Can't start UDP forwarder on port 514: listen udp :514: bind: address already in use

This error occurs because Syslog uses port 514 by default.

To resolve:

- Disable Syslog, OR
- Configure the Agent to listen on a different, available port.

## Support

For further assistance, contact [Datadog support][3].

[1]: https://cloudone.trendmicro.com/
[2]: https://docs.datadoghq.com/help/
[3]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/api/latest/ip-ranges/
[7]: https://github.com/DataDog/integrations-core/blob/master/trend_micro_cloud_one/datadog_checks/trend_micro_cloud_one/data/conf.yaml.example
[8]: https://docs.datadoghq.com/integrations/trend_micro_cloud_one#agent-and-event-forwarder-configuration
[9]: https://docs.datadoghq.com/integrations/trend_micro_cloud_one#file-storage-api-configuration
[10]: https://docs.datadoghq.com/integrations/trend_micro_cloud_one#log-collection
