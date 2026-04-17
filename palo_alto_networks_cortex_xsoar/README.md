## Overview

[Palo Alto Networks Cortex XSOAR][1] is a security orchestration, automation, and unifying incident response (SOAR) platform that helps teams automate incident handling and integrate security tools to enhance SOC efficiency and reduce remediation time.

This integration parses and ingests the following types of logs:

- **Audit Logs**: Capture all administrative user activities within Palo Alto Networks Cortex XSOAR.
- **Incidents**: Capture key details of incidents, including severity, status, type, and ownership, to support tracking and investigation activities in Palo Alto Networks Cortex XSOAR.

You can visualize detailed insights into these logs through the out-of-the-box dashboards. Additionally, ready-to-use Cloud SIEM detection rules are available to help you monitor and respond to potential security threats effectively.

This integration collects the following metrics:

- **Automation Insight Metrics**: Provide visibility into playbook, task, and command execution activity, including counts, failures, and execution duration, to help monitor automation performance, identify errors, and evaluate operational efficiency.
- **API Execution Metrics**: Provide visibility into API execution activity, including total calls and rate-limited requests, to help monitor integration usage, detect throttling events, and evaluate API performance.
- **SLA Metrics**: Provide visibility into incident response timelines, including mean time to detection, triage, containment, and resolution, along with counts of items within and outside SLA thresholds, helping monitor response performance and compliance.

Visualize detailed insights into these metrics through the out-of-the-box dashboards. Additionally, monitors are provided to alert you to any potential issues.

## Setup

### Generate API Key, API Key ID and API URL

1. Sign in to Palo Alto Networks Cortex XSOAR platform.
2. Navigate to **Settings & Info** > **Settings** > **Integrations** > **API Keys**.
3. Click **+ New Key**.
4. Under **Generate API Key**:
   - **Security Level**: Select **Standard**.
   - **Role**: Select **Read-Only**.
5. Click **Generate**.
6. In the **API Keys** table, locate the **ID** field for the created API Key.
7. Click **Copy API URL** to copy the API URL.

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