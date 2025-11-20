# iboss

## Overview

[iboss][1] provides secure internet access and Zero Trust enforcement for users, wherever they are. It combines key security functions such as Secure Web Gateway (SWG), CASB, ZTNA, and DLP into a single, scalable solution. Traffic is routed through iboss's infrastructure to ensure consistent policy enforcement and threat protection.

This integration parses and ingests the following types of logs:

- **Web Logs**: Provides information about client requests to web resources, enabling monitoring of web traffic and policy enforcement.
- **DLP Logs**: Provides information related to data loss prevention, tracking policy enforcement, and potential sensitive data exposures.
- **Audit Logs**: Provides information about user and system activities to ensure traceability and support compliance monitoring.

You can visualize detailed insights into these logs through the out-of-the-box dashboards. Additionally, ready-to-use Cloud SIEM detection rules are available to help you monitor and respond to potential security threats effectively.

This integration collects the following metrics:

- **Gateway Performance**: Provides insights into request volumes, resource utilization, processing times, and error counts to monitor the health and efficiency of iboss gateways.
- **Bandwidth**: Provides information about data usage across domains, users, locations, and protocols, enabling monitoring of network traffic volume and flow patterns.
- **Digital Experience**: Provides insights into user experience by measuring connection times between clients, proxies, and servers across users, assets, and locations.
- **Web**: Provides visibility into user web activity, including site visits, blocks, malware detections, and search trends, to support usage analysis and policy effectiveness.
- **CASB**: Provides insights into cloud app usage, user behavior, and traffic patterns, enabling visibility, threat detection, and enforcement of cloud access policies.
- **Threat**: Provides visibility into detected and prevented threats across users, assets, IPs, and geolocations, enabling threat trend analysis and risk monitoring.
- **Zero Trust**: Provides visibility into users, devices, resources, and traffic, enabling continuous monitoring, trust evaluation, and policy enforcement within the Zero Trust framework.

**Note:** All metrics except for `Gateway Performance` are collected once per day, only after the complete daily iboss report is available.

Visualize detailed insights into these metrics through the out-of-the-box dashboards. Additionally, monitors are provided to alert you to any potential issues.

### Dashboards

#### Logs

Here is the list of dashboards populated using logs:

- iboss - Logs Overview
- iboss - Web & DLP Logs
- iboss - Audit Logs
- iboss - Real-Time Digital Experience Log Analytics
- iboss - Real-Time Web Log Analytics
- iboss - Real-Time Bandwidth Log Analytics
- iboss - Real-Time Zero Trust Log Analytics
- iboss - Real-Time Threat Log Analytics
- iboss - Real-Time CASB Log Analytics

#### Metrics

Here is the list of dashboards populated using metrics:

- iboss - Gateway Performance Metrics
- iboss - Digital Experience Metrics Report
- iboss - Web Analytics Metrics Report
- iboss - Bandwidth Metrics Report
- iboss - Zero Trust Metrics Report
- iboss - Threat Metrics Report
- iboss - CASB Metrics Report


### Monitors

#### Logs

Here is the list of monitors for logs:

- Excessive bandwidth usage detected
- High average application peer time detected
- High rate of unprevented threats detected

#### Metrics

Here is the list of monitors for metrics:

- Anomalous increase in gateway requests per second detected
- High gateway load detected
- High proxy error rate detected
- High proxy response time detected

## Setup

**Note**: The following steps are required only for collecting metrics. For log collection, see the `Log collection` section below.

### Generate API credentials in iboss

To collect metrics, you can either use an existing user with **Full Administrator** access to the **Reporting & Analytics** module, or create a custom user with a custom RBAC group by following the steps to set up reporting-only permissions and assign the user to that RBAC group.

#### Create New RBAC

1. Log into iboss portal as a System Administrator.
2. Go to **Home** > **System Administrators**.
3. Switch to the **Role-Based Access Control** tab.
4. Click **Add Custom RBAC Group**.
5. Enter a **Display Name** for the RBAC.
6. In the **General Info & Permissions** tab, enable only the **Reporting & Analytics** option to limit permissions to reporting only. Next, go to the **Reporting & Analytics Permissions** tab and choose **Full Administrator** from the **Permission Type** dropdown to allow complete access within the reporting module.
7. Click on **Add RBAC Group**.


#### Create New User

1. Log into iboss portal as System Administrator.
2. Go to **Home** > **System Administrators**.
3. Click **Add New System Administrator**.
4. Add details for **System Administrator Email Address**, **First Name**, and **Last Name**.
5. For **Use RBAC Groups**, select the RBAC group with minimal permissions.
6. Click **Add New System Administrator**.

**Note**: Make sure that MFA is disabled for the user account used by this integration.

### Connect your iboss Account to Datadog

1. Add your iboss email address and password.

   | Parameters                        | Description                                                                          |
   | --------------------------------- | ------------------------------------------------------------------------------------ |
   | Email Address                     | The email address of your iboss account.                                             |
   | Password                          | The password of your iboss account.                                                  |
   | Collect gateway performance metrics   | Enable to collect gateway performance metrics from iboss. The default value is `true`. |
   | Collect bandwidth metrics             | Enable to collect bandwidth metrics from iboss. The default value is `true`.           |
   | Collect Digital Experience metrics    | Enable to collect digital experience metrics from iboss. The default value is `true`.  |
   | Collect web metrics                   | Enable to collect web metrics from iboss. The default value is `true`.                 |
   | Collect CASB metrics                  | Enable to collect CASB metrics from iboss. The default value is `true`.                |
   | Collect threat metrics                | Enable to collect threat metrics from iboss. The default value is `true`.              |
   | Collect Zero Trust metrics            | Enable to collect zero trust metrics from iboss. The default value is `true`.          |

2. Click **Save**.

### Installation

**Note**: These steps are only required for collecting logs.
**Minimum Agent version:** 7.69.0

To install the iboss integration, run the following Agent installation command in your terminal, then complete the configuration steps below. For more information, see the [Integration Management][4] documentation.

**Note**: This step is not necessary for Agent version >= 7.69.0 .

```shell
sudo -u dd-agent -- datadog-agent integration install datadog-iboss==1.0.0
```

### Configuration

#### Log collection

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in `datadog.yaml`:

   ```yaml
   logs_enabled: true
   ```

2. Open your `iboss.d/conf.yaml` file, and add the following block to enable log collection.

   See the sample configuration file ([iboss.d/conf.yaml][5]) for available options.

   ```yaml
   logs:
     - type: tcp # or 'udp'
       port: <PORT>
       source: iboss
       service: iboss
   ```

   **Note**:

   - `PORT`: Port should be similar to the port provided in **Configure syslog message forwarding from iboss** section.
   - Datadog recommends that you do not change the service and source values, as these parameters are integral to the pipeline's operation.

3. [Restart the Agent][2].

#### Configure syslog message forwarding from iboss

1. Log into the iboss portal.
2. Navigate to **Integration Marketplace**, then select **Log Forwarding** from the left-hand menu and click the **Configure** button associated with the **Syslog Log Forwarding** widget.
3. Click the **Add Integration** button to add the Syslog integration.
4. Configure the settings as follows:
   - **Forward From**: Select **Reporter** from the dropdown.
   - **Select Reporting Database**: Select the Reporting Database.
   - **Service Name**: Choose a descriptive name for the integration.
   - **Enable Service**: Set this to Enabled.
   - **Log Type**: Select **URL** from the dropdown.
   - **Protocol Type**: Select **UDP** or **TCP** from the dropdown.
   - **Syslog Facility Level**: Select **Facility Syslog** from the dropdown.
   - **Reporting Group**: Select **All** from dropdown.
   - **Host Name**: Enter the fully qualified domain name or IP address of the syslog server.
   - **Port**: Enter the port.
   - **Log Format**: Select **JSON** from the dropdown.
   - **Transfer Interval**: Select **Continuous** from the dropdown.
   - **Field Delimiter**: Select **SPACE** from the dropdown.
   - **Send DLP/Web/DNS/Malware/Audit/ConnectionError Logs**: Set to Enable based on your preference for sending logs.
   - **Fields to Forward**: Add all fields except **DLP Base64 Encoded Meta Data**, **Base64 Encoded Meta Data**, and **Chat GPT Message**.
     <br>After entering the required details, click **Add Service**.

**Note:** 
- If you have multiple reporter nodes, make sure to repeat steps 3 and 4 for each reporter node.
- The `Send Connection Error Logs` toggle in iboss should only be visible if `Send Web Logs` toggle is disabled.

### Validation

[Run the Agent's status subcommand][6] and look for `iboss` under the Logs Agent section.

## Data Collected

### Logs

| Format                    | Event Types                                      |
| ------------------------- | ------------------------------------------------ |
| JSON                      | Web Logs, DLP Logs, Audit Logs                   |

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

<!-- {{< get-metrics-from-git "iboss" >}} -->

### Events

The iboss integration does not include any events.

## Troubleshooting

### Permission denied while port binding

If you see a **Permission denied** error while port binding in the Agent logs:

1. Binding to a port number under 1024 requires elevated permissions. Grant the necessary permissions using the `setcap` command:

   ```shell
   sudo setcap CAP_NET_BIND_SERVICE=+ep /opt/datadog-agent/bin/agent/agent
   ```

2. Verify the setup is correct by running the `getcap` command:

   ```shell
   sudo getcap /opt/datadog-agent/bin/agent/agent
   ```

   You should see output similar to:

   ```shell
   /opt/datadog-agent/bin/agent/agent = cap_net_bind_service+ep
   ```

   **Note**: Re-run this `setcap` command every time you upgrade the Agent.

3. [Restart the Agent][2].

### Data is not being collected

Ensure firewall settings allow traffic through the configured port.

### Port already in use

On systems running Syslog, the Agent may fail to bind to port 514 and display the following error: 
   
    Can't start UDP forwarder on port 514: listen udp :514: bind: address already in use

This error occurs because Syslog uses port 514 by default. 

To resolve:
  - Disable Syslog, OR
  - Configure the Agent to listen on a different, available port.

For further assistance, contact [Datadog support][3].

[1]: https://www.iboss.com/
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[3]: https://docs.datadoghq.com/help/
[4]: https://docs.datadoghq.com/agent/guide/integration-management/?tab=linux#install
[5]: https://github.com/DataDog/integrations-core/blob/master/iboss/datadog_checks/iboss/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/iboss/metadata.csv