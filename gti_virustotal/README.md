## Overview

[Google Threat Intelligence VirusTotal][1] is a crowdsourced repository for threat data. It enables security teams to analyze suspicious files, URLs, domains, and IP addresses to detect malware and other threats by aggregating input from multiple security vendors.

This integration collects the following indicator types:

- IPv4
- Domain
- SHA256

Integrate GTI VirusTotal with Datadog to enhance your security logs with threat intelligence, enabling analysis of matched IOCs through pre-built dashboards. Additionally, the integration can be used for Cloud SIEM detection rules for enhanced monitoring and security.

## Setup

### Obtain an API Key from GTI VirusTotal Platform

1. Log in to the GTI VirusTotal Platform.
2. Click the **Account > API Key** tab.
3. Navigate to the **GTI API Key** section and copy the API key.

### Connect your GTI VirusTotal account to Datadog

1. Provide the following details.
   | Parameter | Description |
   | ---------- | ---------------------------------------------- |
   | API Key | The API Key of your GTI VirusTotal account. |
   | Collect IPv4 IOCs | Enable to collect IPv4 IOCs. The default value is true.  |
   | Collect Domain IOCs | Enable to collect Domain IOCs. The default value is true.  |
   | Collect SHA256 IOCs | Enable to collect SHA256 IOCs. The default value is true. |
2. Click **Save**.

## Troubleshooting

Need help? Contact [Datadog support][2].

[1]: https://www.virustotal.com/gui/home/search
[2]: https://docs.datadoghq.com/help/