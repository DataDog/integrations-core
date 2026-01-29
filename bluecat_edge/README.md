## Overview

[BlueCat Edge][1] enables centralized collection of DNS query logs, providing enhanced visibility into DNS traffic for monitoring, analysis, and operational insights.

This integration ingests the DNS Query Logs.

Integrate BlueCat Edge with Datadog to analyze alerts and audit logs using pre-built dashboards. Datadog parses and enriches these logs using built-in log pipelines, supporting search and analysis. You can also use this data with Cloud SIEM detection rules for security monitoring.

## Setup

### Generate an API credentials in BlueCat Edge

1. Log in to the BlueCat Edge dashboard and navigate to Account.
2. Select the Profile tab.
3. In the Access key sets section, click New.
4. The Client ID and Secret Key are displayed.
5. Identify your Bluecat Edge Domain URL by checking your URL.
	- If your URL is https://myBlueCat.edge.bluec.at/, the BlueCat Edge Domain is myBlueCat.edge.bluec.at.

### Connect your BlueCat Edge account to Datadog

1. Add your `Region` and `API key`.
   | Parameter | Description |
   | ---------- | ---------------------------------------------- |
   | BlueCat Edge Domain | Bluecat Edge Domain of Instance. |
   | Client ID | Client ID of BlueCat Edge. |
   | Client Secret | Client Secret of BlueCat Edge. |
2. Click **Save**.

## Data Collected

### Logs

The BlueCat Edge integration collects DNS Query logs and forwards them to Datadog.

### Metrics

The BlueCat Edge integration does not include any metrics.

### Events

The BlueCat Edge integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][2].

[1]: https://bluecatnetworks.com/products/edge/
[2]: https://docs.datadoghq.com/help/
