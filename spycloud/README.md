## Overview
[SpyCloud](https://spycloud.com/) recaptures exposed identity data from the criminal underground, including breaches, malware infections, and phishing activity, and makes this raw stolen data actionable for security teams.

This integration collects the following indicator types:
- IP
- Domain

Integrate SpyCloud with Datadog to enrich your security logs with threat intelligence and analyze matched indicators of compromise (IOCs) through pre-built dashboards. The integration also feeds Cloud SIEM detection rules.

## Setup

### Obtain an API key from the SpyCloud Customer Portal

1. Log in to your SpyCloud Customer Portal.
2. Navigate to the **API** tab in the sidebar.
3. In the **Keys** section, copy the **API key**.

### Connect your SpyCloud account to Datadog

1. In Datadog, on the SpyCloud integration tile, provide the following details:
   | Parameter | Description |
   | ---------- | ---------------------------------------------- |
   | API key | The API key for your SpyCloud account. |
   | Collect IP IOCs | Whether to collect IP IOCs from SpyCloud. Enabled by default. |
   | Collect Domain IOCs | Whether to collect domain IOCs from SpyCloud. Enabled by default. |
   
2. Click **Save**.

## Data Collected

The SpyCloud integration does not include any metrics, service checks, or events.

## Troubleshooting

Need help? Contact [Datadog support](https://docs.datadoghq.com/help/).