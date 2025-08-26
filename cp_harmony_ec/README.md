# Agent Check: cp_harmony_ec


## Overview

[Checkpoint Harmony Email and Collaboration][1] provides advanced protection for email and collaboration platforms such as Microsoft 365 and Google Workspace. It analyzes email content, user behavior, and threat indicators to detect phishing attempts, malware, and data leaks, helping organizations secure sensitive information and maintain business continuity.

This integration enables visibility into threat types, user targeting patterns, sender activity, and domain-level log analytics. Pre-built dashboard visualizations provide additional insights to help detect anomalies and assess security posture.

## Setup

Set up the [Datadog Forwarder][2].

Configure an [AWS S3 bucket to receive logs][3].

The Datadog Agent is not required for this integration.

### Configuration

**Configuring the Checkpoint Harmony Email and Collaboration platform to send logs to your S3 bucket**
- Refer to this [link][4] to more on this.

### Validation

After setup, verify that logs appear in Datadog by checking the Logs Explorer.

## Data Collected

### Metrics

The Checkpoint Harmony Email and Collaboration integration does not include any metrics.

### Events

The Checkpoint Harmony Email and Collaboration integration does not include any events.

### Service Checks

The Checkpoint Harmony Email and Collaboration integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][5].


[1]: https://www.checkpoint.com/harmony/email-security/
[2]: https://docs.datadoghq.com/logs/guide/forwarder/?tab=cloudformation
[3]: https://sc1.checkpoint.com/documents/Harmony_Email_and_Collaboration/Topics-Harmony-Email-Collaboration-Admin-Guide/Managing-Security-Events/SIEM.htm#Configuring_AWS_S3_to_Receive_Harmony_Email_&_Collaboration_Logs
[4]: https://sc1.checkpoint.com/documents/Harmony_Email_and_Collaboration/Topics-Harmony-Email-Collaboration-Admin-Guide/Managing-Security-Events/SIEM.htm#Configuring%20SIEM%20Integration
[5]: https://docs.datadoghq.com/help/