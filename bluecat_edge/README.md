## Overview

[BlueCat Edge][1] is an intelligent DNS resolver and caching layer that leverages existing DNS infrastructure to provide unprecedented visibility and control over DNS traffic.

This integration ingests the DNS query logs.

- **DNS Query Logs**: Logs that capture DNS request and response activity, including queried domains and source clients.

Integrate BlueCat Edge with Datadog to analyze DNS query logs using pre-built dashboards. Datadog parses and enriches these logs using built-in log pipelines, supporting search and analysis. You can also use this data with Cloud SIEM detection rules for security monitoring.

## Setup

### Generate an API credentials in BlueCat Edge

1. Log in to **BlueCat Edge** using a user with the **Analyst** role or higher.
2. Click on **Account > Profile** tab.
3. In the **Access key sets** section, click **New**.
4. The **Client ID** and **Secret key** are displayed.
5. Identify your **BlueCat Edge Domain URL** using the URL of your BlueCat Edge cloud instance.
   - For example, if your BlueCat Edge cloud instance URL is **https://myBlueCat.edge.bluec.at/**, the BlueCat Edge Domain URL is **myBlueCat.edge.bluec.at**.

### Connect your BlueCat Edge account to Datadog

1. Add your `BlueCat Edge Domain`, `Client ID` and `Secret key`.
   | Parameter | Description |
   | ---------- | ---------------------------------------------- |
   | BlueCat Edge Domain | The BlueCat Edge domain of the instance. |
   | Client ID | Client ID of BlueCat Edge. |
   | Secret key | Secret key of BlueCat Edge. |
   | Collect NOERROR DNS Query Logs | Control the collection of NOERROR DNS Query Logs. Enabled by default. |
2. Click **Save**.

## Data Collected

### Logs

The BlueCat Edge integration collects DNS query logs and forwards them to Datadog.

### Metrics

The BlueCat Edge integration does not include any metrics.

### Events

The BlueCat Edge integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][2].

[1]: https://bluecatnetworks.com/products/edge/
[2]: https://docs.datadoghq.com/help/
