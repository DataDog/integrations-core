## Overview

[Valence Security][1] is a SaaS security platform that protects cloud applications by discovering, monitoring, and remediating risks across business applications. It reduces exposure from misconfigurations, third-party integrations, and identity threats across SaaS environments.

This integration ingests the following log types:

- **Alerts**: Logs that capture detected SaaS security risks, including suspicious activity, misconfigurations, identity threats, and data exposure across cloud applications.
- **Audit logs**: Logs that capture user and system activity, including configuration changes, access events, and administrative actions.

Integrate Valence Security with Datadog to analyze alerts and audit logs using pre-built dashboards. Datadog parses and enriches these logs using built-in log pipelines, supporting search and analysis. You can also use this data with Cloud SIEM detection rules for security monitoring.

## Setup

### Generate an API key in Valence Security

1. Log in to the Valence Security platform using an admin account.
2. Navigate to **Administration** > **Settings** > **Valence API**.
3. Click **+ Generate API Key** and provide the following details:
   - **API key description**: A description of the API key’s purpose.
   - **Display name**: A user-friendly name to identify the API key.
   - **Role**: The role associated with the API key (select **Admin**).
4. Click **Generate** and copy the API key.
5. Identify your Valence Security region by checking the hostname suffix of your URL:
   - `app.valencesecurity.com`: US
   - `appeu.valencesecurity.com`: EU

### Connect your Valence Security Account to Datadog

1. Add your `Region` and `API Key`.
   | Parameter | Description |
   | ---------- | ---------------------------------------------- |
   | Region | The Valence Security region. |
   | API Key | The Valence Security API key. |
   | Get Alerts | Collect alert logs from Valence Security (enabled by default). |
   | Get Audit Logs | Collect audit logs from Valence Security (enabled by default).  |
2. Click **Save**.

## Data Collected

### Logs

The Valence Security integration collects alerts and audit logs and forwards them to Datadog.

### Metrics

The Valence Security integration does not include any metrics.

### Events

The Valence Security integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][2].

[1]: https://www.valencesecurity.com/
[2]: https://docs.datadoghq.com/help/
