# Agent Check: cp_harmony_ec

[Checkpoint Harmony Email and Collaboration][1] specializes in cybersecurity for cloud-based communication platforms by providing advanced protection for email and collaboration tools such as Microsoft 365 and Google Workspace. By analyzing email content, user behavior, and threat indicators, Harmony enables features like phishing prevention, malware detection, and data leak protection. This functionality is crucial for safeguarding sensitive information, ensuring business continuity, and enhancing organizational security posture.

## Overview

Here are some insights that can be drawn from the dashboard:

- **Threat Activity Trends**: Monitor types of threats and suspicious email behavior over time.
Targeted User Analysis: Identify and track the most frequently targeted users.
- **Sender Insights**: Analyze top sender IP addresses and domains to detect recurring threat sources.
- **Log Volume Breakdown**: View log volume segmented by matched security tools and verdicts.
- **Confidence Level Monitoring**: Track trends in detection confidence levels to assess alert reliability.
- **Domain-Level Analytics**: Examine log volume by customer domain for focused security insights.
- **Behavioral Monitoring**: Evaluate user and domain behaviors to identify anomalies and potential threats.

## Setup

**Setting up Datadog Forwarder**
- Refer to this link to know on how to setup [Datadog Forwarder][2]

**Configuring AWS S3 to Receive Harmony Email & Collaboration Logs**
- Refer to this link to know on how to send logs to AWS S3 bucket. [link][3]

### Installation

The Datadog Agent need not be installed for this integration.

### Configuration

**Configuring the Checkpoint Harmony Email and Collaboration platform to send logs to your S3 bucket**
- Refer to this [link][4] to more on this.

### Validation

Once the configuration is done, you can validate it by confirming if the logs are being ingested in Datadog Platform.

## Data Collected

### Metrics

cp_harmony_ec does not include any metrics.

### Events

The cp_harmony_ec integration does not include any events.

### Service Checks

The cp_harmony_ec integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][5].


[1]: https://www.checkpoint.com/harmony/email-security/
[2]: https://docs.datadoghq.com/logs/guide/forwarder/?tab=cloudformation
[3]: https://sc1.checkpoint.com/documents/Harmony_Email_and_Collaboration/Topics-Harmony-Email-Collaboration-Admin-Guide/Managing-Security-Events/SIEM.htm#Configuring_AWS_S3_to_Receive_Harmony_Email_&_Collaboration_Logs
[4]: https://sc1.checkpoint.com/documents/Harmony_Email_and_Collaboration/Topics-Harmony-Email-Collaboration-Admin-Guide/Managing-Security-Events/SIEM.htm#Configuring%20SIEM%20Integration
[5]: https://docs.datadoghq.com/help/