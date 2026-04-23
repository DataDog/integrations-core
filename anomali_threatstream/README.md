## Overview

[Anomali ThreatStream][1] is a threat intelligence platform (TIP) that automates the collection, curation, and analysis of threat data from global, open-source, and premium feeds.

This integration collects the following indicator types:

- IPv4
- Domain
- SHA256

Integrate Anomali ThreatStream with Datadog to enhance your security logs with threat intelligence, enabling analysis of matched IOCs through pre-built dashboards. Additionally, the integration can be used for Cloud SIEM detection rules for enhanced monitoring and security.

## Setup

### Obtaining Anomali ThreatStream API Credentials and Domain

1. Log in to the Anomali ThreatStream instance.
2. Navigate to **Settings** > **My profile**.
3. Under Account Information, Click **Reveal** next to the **API Key** and copy it. Also, copy your **Email**.
4. Identify your Anomali ThreatStream Domain using the URL of your Anomali ThreatStream instance.
   - For example, if your Anomali ThreatStream instance URL is `https://ui.threatstream.com/` then Anomali ThreatStream Domain is `ui.threatstream.com`.

### Connect your Anomali ThreatStream account to Datadog

1. Provide following details.
   | Parameter | Description |
   | ---------- | ---------------------------------------------- |
   | Domain | Domain of the Anomali ThreatStream. |
   | Email | Email address associated with your ThreatStream account. |
   | API Key | API key of your Anomali ThreatStream account. |
   | Collect IPv4 IOCs | Enable to collect IPv4 IOCs. The default value is true. |
   | Collect Domain IOCs | Enable to collect Domain IOCs. The default value is true. |
   | Collect SHA256 IOCs | Enable to collect SHA256 IOCs. The default value is true. |
2. Click **Save**.

## Troubleshooting

Need help? Contact [Datadog support][2].

[1]: https://www.anomali.com/products/threatstream
[2]: https://docs.datadoghq.com/help/
