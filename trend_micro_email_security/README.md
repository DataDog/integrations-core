## Overview

[Trend Micro Email Security][1] is a cloud-based solution that stops phishing, ransomware, and business email compromise (BEC) attacks. This solution uses a combination of cross-generational threat techniques, like machine learning, sandbox analysis, data loss prevention (DLP), and other methods to stop all types of email threats.

This integration ingests the following logs:

- Policy events and detection - These logs provide information about policy events and detection, allowing you to monitor and respond to potential security threats effectively.
- Mail tracking - These logs provide information about email activities, including accepted and blocked traffic, allowing you to track email messages that have passed through the system and monitor their delivery status.

Use out-of-the-box dashboards to visualize detailed insights into email traffic analysis, real-time threat detection, security detection and observation, and compliance monitoring.

## Setup

### Generate API credentials in Trend Micro Email Security

1. Log on to the Trend Micro Email Security administrator console.
2. Navigate to **Administration** > **Service Integration** > **API Access**.
3. Click **Add** to generate an API Key.
4. Switch to the **Log Retrieval** tab and Ensure the **status** for log retrieval is enabled.
5. To identify the **Host Region** of your Trend Micro Email Security, please refer this [link][3].
6. **Username** is **Login ID** of your Trend Micro Email Security console.

### Connect your Trend Micro Email Security Account to Datadog

1. Add your host region, username, and API key.
    | Parameters  | Description                                                           |
    | ----------- | --------------------------------------------------------------------- |
    | Host Region | The region of the Trend Micro Email Security administrator console.   |
    | Username    | The username of the Trend Micro Email Security administrator console. |
    | API Key     | The API key of the Trend Micro Email Security administrator console.  |

2. Click the **Save** button to save your settings.

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