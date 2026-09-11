## Overview

[Anomali ThreatStream][1] is a threat intelligence platform (TIP) that automates the collection, curation, and analysis of threat data from global, open-source, and premium feeds.

This integration collects the following indicator types:

- IPv4
- Domain
- SHA256

Integrate Anomali ThreatStream with Datadog to enhance your security logs with threat intelligence, enabling analysis of matched Indicators of Compromise (IOCs) through pre-built dashboards. Additionally, the integration can be used for Cloud SIEM detection rules for enhanced monitoring and security.

## Setup

### Obtain Anomali ThreatStream API credentials and API domain

1. Log in to the Anomali ThreatStream instance.
2. Navigate to **Settings** > **My profile**.
3. Under **Account Information**, click **Reveal** next to the **API Key** and copy it. Also, copy your **Email**.
4. Identify your API domain from the [Anomali ThreatStream access documentation][3]:
   - For US Cloud, use `api.threatstream.com`.
   - For EU Cloud, use `api-eu.threatstream.com`.
   - Enter only the API domain, without `https://` or an `/api/...` path. Do not enter the platform domain (`ui.threatstream.com` or `ui-eu.threatstream.com`).

### Connect your Anomali ThreatStream account to Datadog

1. Provide the following details:
   | Parameter | Description |
   | ---------- | ---------------------------------------------- |
   | API Domain | Your Anomali ThreatStream API domain; for example, `api.threatstream.com` for US Cloud or `api-eu.threatstream.com` for EU Cloud. |
   | Email | Email address associated with your ThreatStream account. |
   | API Key | API key of your Anomali ThreatStream account. |
   | Collect IPv4 IOCs | Enable to collect IPv4 IOCs. The default value is `true`. |
   | Collect Domain IOCs | Enable to collect Domain IOCs. The default value is `true`. |
   | Collect SHA256 IOCs | Enable to collect SHA256 IOCs. The default value is `true`. |
2. Click **Save**.

## Troubleshooting

Need help? Contact [Datadog support][2].

[1]: https://www.anomali.com/products/threatstream
[2]: https://docs.datadoghq.com/help/
[3]: https://docs.anomali.com/Content/Getting%20Started%20with%20ThreatStream/access_optic.htm
