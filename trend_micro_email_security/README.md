## Overview

[Trend Micro Email Security][1] is a cloud-based solution that stops phishing, ransomware, and business email compromise (BEC) attacks. This solution uses a combination of cross-generational threat techniques, like machine learning, sandbox analysis, data loss prevention (DLP), and other methods to stop all types of email threats.

This integration ingests the following logs:

- Policy events and detection
- Mail tracking

Use out-of-the-box dashboards to visualize detailed insights into email traffic analysis, real-time threat detection, security detection and observation, and compliance monitoring.

## Setup

### Configuration

#### Get Credentials of Trend Micro Email Security

1. Log on to the Trend Micro Email Security administrator console.
2. Navigate to **Administration** > **Service Integration** > **API Access**.
3. Click **Add** to generate an API Key.
4. Switch to the **Log Retrieval** tab and Ensure the **status** for log retrieval is enabled.
5. To identify the **Host Region** of your Trend Micro Email Security, please refer this [link][3].
6. **Username** is **Login ID** of your Trend Micro Email Security console.

#### Add your Trend Micro Email Security Credentials

- Host Region
- Username
- API key

## Data Collected

### Logs

The Trend Micro Email Security integration collects and forwards policy events and detection and mail tracking to Datadog.

### Metrics

The Trend Micro Email Security integration does not include any metrics.

### Events

The Trend Micro Email Security integration does not include any events.

## Support

For any further assistance, contact [Datadog support][2].

[1]: https://www.trendmicro.com/en_in/business/products/user-protection/sps/email-and-collaboration/email-security.html
[2]: https://docs.datadoghq.com/help/
[3]: https://success.trendmicro.com/en-US/solution/KA-0016673#:~:text=Trend%20micro%20email%20security