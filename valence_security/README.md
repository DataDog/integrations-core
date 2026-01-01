## Overview

[Valence Security][1] is SaaS security platform that protects cloud applications by discovering, monitoring, and remediating risks across business apps. It reduces exposure from misconfigurations, third-party integrations, and identity threats, ensuring continuous compliance and data protection for SaaS environments.

This integration ingests the following logs:

- **Alerts**: These logs provide detailed visibility into SaaS security risks by detecting suspicious activities, misconfigurations, identity threats, and data exposure across cloud applications.
- **Audit Logs**: These logs provide detailed visibility into user and system activities, capturing configuration changes, access events, and administrative actions.

Integrate Valence Security with Datadog to gain insights into alerts and audit logs using pre-built dashboard visualizations. Datadog uses its built-in log pipelines to parse and enrich these logs, facilitating easy search and detailed insights. Additionally, the integration can be used with Cloud SIEM detection rules for enhanced monitoring and security.

## Setup

### Generate API Key from the Valence Security

1. Log in to Valence Security platform using the admin account.
2. Navigate to **Administration** > **Settings** > **Valence API**.
3. Click the **+ Generate API Key** and provide the following details:
   - API Key Description: Description of the API Key purpose
   - Display Name: A user-friendly name to identify API Key
   - Role: From the dropdown, select **Admin**.
4. Click **Generate** and Copy the API key.
5. Identify your Valence Security region by checking the hostname suffix of your URL:
   - app.valencesecurity.com -> US
   - appeu.valencesecurity.com -> EU

### Connect your Valence Security Account to Datadog

1. Add your `Region` and `API Key`.
   | Parameters | Description |
   | ---------- | ---------------------------------------------- |
   | Region | The Region of your Valence Security |
   | API Key | The API Key of your Valence Security |
   | Get Alerts | Control the collection of Alerts from Valence Security. <br> Enabled by default.|
   | Get Audit Logs | Control the collection of Audit Logs from Valence Security. <br> Enabled by default.|
2. Click **Save**.

## Data Collected

### Logs

The Valence Security integration collects and forwards alerts and audit logs to Datadog.

### Metrics

The Valence Security integration does not include any metrics.

### Events

The Valence Security integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][2].

[1]: https://www.valencesecurity.com/
[2]: https://docs.datadoghq.com/help/
