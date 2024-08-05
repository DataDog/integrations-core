## Overview

[Cisco Secure Email Threat Defense][1] is an integrated cloud-native security solution for Microsoft 365 that focuses on simple deployment, easy attack remediation, and providing superior visibility into inbound, outbound, and internal user-to-user messages. It detects phishing, scam, malicious and BEC types of threats using advanced threat detection capabilities and resolves them in real time.

This integration ingests the following logs:
- Message: Message logs provide detailed information about email communications, including sender, recipient, timestamps, subject, and threat-related data for analysis and monitoring.

The Cisco Secure Email Threat Defense integration provides out-of-the-box dashboards so you can gain insights into the Cisco Secure Email Threat Defense's message logs, enabling quick and necessary actions. Additionally, out-of-the-box detection rules are available to help you monitor and respond to potential security threats effectively.


## Setup

### Configuration

#### Get API Credentials for Cisco Secure Email Threat Defense 


#### Steps to generate API key, Client ID and Client Password:
1. Login to Cisco Secure Email Threat Defense UI.
2. Navigate to `Administration` and select the `API Clients` tab.
3. Click on `Add New Client` to generate the `Client ID` and `Client Password`.
4. Enter the `Client Name` and an optional description, then click `Submit`. This will generate your Client ID and Password.
    **Note**: Be sure to save the Client Password, as it will only be displayed once.
5. Additionally, retrieve the `API key` from the API Key section, as the API key must be included in the header for the request.

#### Cisco Secure Email Threat Defense Datadog Integration Configuration

Configure the Datadog endpoint to forward Cisco Secure Email Threat Defense logs to Datadog.

1. Navigate to `Cisco Secure Email Threat Defense`.
2. Add your Cisco Secure Email Threat Defense credentials and verdict delay.

| Cisco Secure Email Threat Defense Parameters | Description  |
| -------------------- | ------------ |
| Host Name               | The Host Name for Cisco Secure Email Threat Defense.|
| API Key           | API Key from Cisco Secure Email Threat Defense.         |
| Client ID      | Client ID from Cisco Secure Email Threat Defense.    |
| Client Password      | Client Password from Cisco Secure Email Threat Defense.    |
| Verdict Delay      | Time (in minutes) required to allow verdicts to be updated.    |

**Note**: Please specify the Verdict Delay as a number between 0 to 720 minutes. For example, you might use 30 or 0.5. The recommended value for Verdict Delay is 30 minutes. 

## Data Collected

### Logs

The Cisco Secure Email Threat Defense integration collects and forwards Cisco Secure Email Threat Defense message logs to Datadog. This integration will ingest messages with verdict value of scam, malicious, phishing, BEC, spam, graymail, neutral.

**Note**: Please be aware that events will be fetched with a delay according to the time specified in the Verdict Delay. This delay is intended to accommodate retrospective verdicts. However, this does not guarantee that all retrospective verdicts will be processed within this timeframe, as the time required for updates is uncertain.


### Metrics

The Cisco Secure Email Threat Defense integration does not include any metrics.

### Events

The Cisco Secure Email Threat Defense integration does not include any events.

## Support

For further assistance, contact [Datadog Support][2].

[1]: https://www.cisco.com/site/us/en/products/security/secure-email/index.html?dtid=osscdc000283
[2]: https://docs.datadoghq.com/help/