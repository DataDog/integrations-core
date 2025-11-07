## Overview

[Cisco Secure Email Threat Defense][1] is an integrated cloud-native security solution for Microsoft 365. It focuses on simple deployment, easy attack remediation, and providing superior visibility into inbound, outbound, and internal user-to-user messages.

This integration ingests the following logs:
- Message: Message logs provide detailed information about email communications, including sender, recipient, timestamps, subject, and threat-related data for analysis and monitoring.

The Cisco Secure Email Threat Defense integration provides out-of-the-box dashboards so you can gain insights into Cisco Secure Email Threat Defense's message logs, enabling you to take necessary action. Additionally, out-of-the-box detection rules are available to help you monitor and respond to potential security threats effectively.

**Disclaimer**: Your use of this integration, which may collect data that includes personal information, is subject to your agreements with Datadog. Cisco is not responsible for the privacy, security or integrity of any end-user information, including personal data, transmitted through your use of the integration.

## Setup

### Generate API credentials in Cisco Secure Email Threat Defense

1. Log into the Cisco Secure Email Threat Defense UI.
2. Navigate to **Administration** and select the **API Clients** tab.
3. Click on **Add New Client**.
4. Enter a **Client Name** and an optional description.
5. Click on **Submit**. This generates your **Client ID** and **Client Password**.
6. Retrieve the API key from the **API Key** section.

### Connect your Cisco Secure Email Threat Defense Account to Datadog

1. Add your Cisco Secure Email Threat Defense credentials

    | Parameters | Description |
    | ---------- | ----------- |
    | Host Name | Host name is based on the region where your Cisco Secure Email Threat Defense server is located. For details, please reach out to your system administrator. |
    | Client ID | Client ID from Cisco Secure Email Threat Defense account. |
    | Client Password | Client password from your Cisco Secure Email Threat Defense account. |
    | API Key | API key from your Cisco Secure Email Threat Defense account. |
    | Verdict Delay | Events are fetched with a delay according to the time (in minutes) specified in the Verdict Delay. |


2. Click the **Save** button to save your settings.


## Data Collected

### Logs

The Cisco Secure Email Threat Defense integration collects and forwards Cisco Secure Email Threat Defense message logs to Datadog. This integration will ingest messages with verdict values of scam, malicious, phishing, BEC, spam, graymail, and neutral.

**Note**: Events are fetched with a delay according to the time specified in the Verdict Delay. This delay is necessary to ensure that the logs include retrospective verdicts. However, this does not guarantee that all retrospective verdicts are captured within this timeframe, as the time required for updates can vary. For complete verdict information, please log in to your Cisco Secure Email Threat Defense system.

### Metrics

The Cisco Secure Email Threat Defense integration does not include any metrics.

### Events

The Cisco Secure Email Threat Defense integration does not include any events.

## Support

For further assistance, contact [Datadog Support][2].

[1]: https://www.cisco.com/site/us/en/products/security/secure-email/index.html?dtid=osscdc000283
[2]: https://docs.datadoghq.com/help/