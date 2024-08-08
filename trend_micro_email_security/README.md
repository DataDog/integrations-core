## Overview

[Trend Micro Email Security][1] is a cloud-based solution that stops phishing, ransomware, and Business Email Compromise (BEC) attacks. This solution uses an optimum blend of cross-generational threat techniques, like machine learning, sandbox analysis, data loss prevention (DLP), and other methods to stop all types of email threats.

This integration ingests the following logs:

- Policy Events/Detection
- Mail Tracking

Using out-of-the-box dashboards, you can visualize detailed insights into email traffic analysis, real time threat detection, security detection and observation, and compliance monitoring.

## Setup

### Configuration

#### Get Credentials(API Key) of Trend Micro Email Security

1. Log on to the Trend Micro Email Security administrator console.
2. Go to Administration -> Service Integration.<br> The API Access tab displays by default.
3. Click Add to generate an API Key.<br> The API Key is the global unique identifier for your application to authenticate its access to Trend Micro Email Security.
4. Copy the API Key value and save the value. Keep the API Key private.<br> If you want to change your API Key later on, click Add to generate a new key and use the new key in your requests. You can click the toggle button under Status to disable the old key or delete it if both of the following conditions are met:
   1. Requests can be sent successfully with the new key.
   2. The old key is not used by any other applications that have access to Trend Micro Email Security.

#### Trend Micro Email Security DataDog Integration Configuration

Configure the Datadog endpoint to forward Trend Micro Email Security logs to Datadog.

1. Navigate to `Trend Micro Email Security`.
2. Add your Trend Micro Email Security credentials.

| Trend Micro Email Security Parameters | Description                                                          |
| ------------------------------------- | -------------------------------------------------------------------- |
| Host Region                           | The Region of the Trend Micro Email Security administrator console   |
| Username                              | The Username of the Trend Micro Email Security administrator console |
| API Key                               | The API Key of the Trend Micro Email Security administrator console  |

## Data Collected

### Logs

The Trend Micro Email Security integration collects and forwards Policy Events/Detection and Mail Tracking to Datadog.

### Metrics

The Trend Micro Email Security integration does not include any metrics.

### Events

The Trend Micro Email Security integration does not include any events.

## Support

For any further assistance, contact [Datadog support][2].

[1]: https://www.trendmicro.com/en_in/business/products/user-protection/sps/email-and-collaboration/email-security.html
[2]: https://docs.datadoghq.com/help/