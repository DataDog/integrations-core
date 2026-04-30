## Overview
[SpyCloud](https://spycloud.com/) recaptures exposed identity data from the criminal underground, including breaches, malware infections, and phishing activity, and makes this raw stolen data actionable for security teams.

This integration collects the following indicator types:
- IP
- Domain

Integrate SpyCloud with Datadog to enrich your security logs with threat intelligence and analyze matched IOCs through pre-built dashboards. The integration also feeds Cloud SIEM detection rules.

## Setup

### Obtain an API key from the SpyCloud Customer Portal

1. Log in to your SpyCloud Customer Portal.
2. Navigate to the **API** tab in the sidebar.
3. In the **Keys** section, copy the **API Key**.

### Connect your SpyCloud account to Datadog

1. Provide the following details:
   | Parameter | Description |
   | ---------- | ---------------------------------------------- |
   | API Key | The API Key of your SpyCloud account. |
   | Collect IP IOCs | Enable to collect IP IOCs. Enabled by default. |
   | Collect Domain IOCs | Enable to collect Domain IOCs. Enabled by default. |
   
2. Click **Save**.

## Troubleshooting

Need help? Contact [Datadog support](https://docs.datadoghq.com/help/).