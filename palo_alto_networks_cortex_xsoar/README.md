## Overview

[Palo Alto Networks Cortex XSOAR][1] is a security orchestration, automation, and unifying incident response (SOAR) platform that helps teams automate incident handling and integrate security tools to enhance SOC efficiency and reduce remediation time.

This integration parses and ingests the following types of logs:

- **Audit Logs**: Provides visibility into audit activities including configuration changes, user authentication patterns within the Palo Alto Networks Cortex XSOAR platform.
- **Incidents**: Provides visibilities into incidents from Palo Alto Networks Cortex XSOAR. 

You can visualize detailed insights into these logs through the out-of-the-box dashboards. Additionally, ready-to-use Cloud SIEM detection rules are available to help you monitor and respond to potential security threats effectively.

This integration collects the following metrics:

- **Playbook Execution Count**: Represents the total number of playbook executions recorded within the selected time range, indicating the level of automation activity and operational workload.
- **Playbook Execution Failed Count**: Represents the total number of playbook executions that ended in failure within the selected time range, helping identify automation issues, monitor reliability, and track error trends.
- **playbook_execution Average Duration**: Represents the average time taken to complete playbook executions within the selected time range, helping evaluate automation performance and identify delays in workflows.
- **Command Execution Count**: Represents the total number of command executions within the selected time range, helping measure automation activity, track integration usage, and monitor operational workload.
- **Command Execution Failed Count**: Represents the total number of command executions that resulted in failure within the selected time range, helping identify integration issues, monitor reliability, and track error trends.
- **Task Execution Count**: Represents the total number of task executions within the selected time range, helping measure workflow activity, monitor automation usage, and understand operational workload.
- **Task Execution Failed Count**: Represents the total number of task executions that resulted in failure within the selected time range, helping identify workflow issues, monitor reliability, and track error trends.
- **Rate Limited API Call Count**: Represents the total number of API calls that were rate limited within the selected time range, helping identify throttling events, monitor integration limits, and track potential performance impacts.
- **API Execution Count**: Represents the total number of API executions within the selected time range, helping measure integration activity, monitor usage patterns, and understand operational workload.
- **Withing SLA Count**: Represents the total number of items completed within the defined Service Level Agreement (SLA) timeframe, helping measure operational efficiency, track compliance, and monitor response performance.
- **Late SLA Count**: Represents the total number of items that exceeded the defined Service Level Agreement (SLA) timeframe within the selected period, helping track delays, monitor compliance gaps, and identify areas impacting response performance.

**Note:** All metrics are collected at 5-minute intervals.

Visualize detailed insights into these metrics through the out-of-the-box dashboards. Additionally, monitors are provided to alert you to any potential issues.

### Monitors

#### Metrics

Here is the list of monitors for metrics:

- Anomalous spikes in playbook execution failure
- High integration error rate alert
- Connectivity errors per integration alert

## Setup

### Generate API Key

1. Sign in to Palo Alto Networks Cortex XSOAR platform.
2. Navigate to **Settings & Info** > **Settings** > **Integrations** > **API Keys**.
3. Click **+ New Key**.
4. Under **Generate API Key**:
   - **Security Level**: Select **Standard**.
   - **Role**: Select **Read-Only**.
5. Click **Generate**.

### Get API Key ID 
1. Navigate to **Settings & Info** > **Settings** > **Integrations** > **API Keys**
1. In the **API Keys** table, locate the **ID** field for created API Key.

### Get FQDN
1. Navigate to **Settings & Info** > **Settings** > **Integrations** > **API Keys**.
2. Click **Copy API URL**.

### Connect your Palo Alto Networks Cortex XSOAR account to Datadog

1. Add your `API Key`, `API Key ID` and `API URL`.
   | Parameter | Description |
   | ---------- | ---------------------------------------------- |
   | API Key | The Palo Alto Networks Cortex XSOAR API key. |
   | API Key ID | The Palo Alto Networks Cortex XSOAR API key ID. |
   | API URL | The Palo Alto Networks Cortex XSOAR API URL. |
   | Get Incidents | Control the collection of Incidents from Palo Alto Networks Cortex XSOAR. Enabled by default. |
   | Get Audit Logs | Control the collection of Audit Logs from Palo Alto Networks Cortex XSOAR. Enabled by default.  |
   | Get Automation Insight Metrics | Control the collection of Automation Insights from Palo Alto Networks Cortex XSOAR. Enabled by default.  |
   | Get API Execution Metrics | Control the collection of API Executions from Palo Alto Networks Cortex XSOAR. Enabled by default.  |
   | Get SLA Metrics | Control the collection of SLA Insights from Palo Alto Networks Cortex XSOAR. Enabled by default.  |
2. Click **Save**.

## Data Collected

### Logs

The Palo Alto Networks Cortex XSOAR integration collects incidents and audit logs and forwards them to Datadog.

### Metrics

The Palo Alto Networks Cortex XSOAR integration collects and forwards Automation Insight, API Execution and SLA metrics to Datadog.

{{< get-metrics-from-git "palo-alto-networks-cortex-xsoar" >}}

### Events

The Palo Alto Networks Cortex XSOAR integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][2].

[1]: https://www.paloaltonetworks.com/cortex/cortex-xsoar
[2]: https://docs.datadoghq.com/help/