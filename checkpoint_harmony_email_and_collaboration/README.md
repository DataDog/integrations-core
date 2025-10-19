# Check Point Harmony Email & Collaboration

## Overview

[Check Point Harmony Email & Collaboration][1] is a security solution that protects cloud-based email and collaboration platforms from cyber threats like malware, phishing, and data loss.

This integration provides enrichment and visualization for Phishing, Malware, Malicious URL, DLP, Anomaly, Shadow IT, and Spam event types.

Get detailed visibility into these events with out-of-the-box dashboards, and strengthen security with pre-built Cloud SIEM detection rules for proactive threat monitoring and response.

**Minimum Agent version:** 7.64.2

## Setup

Follow the instructions below to configure this integration for your Check Point Harmony Email & Collaboration account.

### Configuration

#### Webhook Configuration

Configure the Datadog endpoint to forward Check Point Harmony Email & Collaboration events as logs to Datadog.

1. Copy the generated URL inside the **Configuration** tab on the Datadog [Check Point Harmony Email & Collaboration integration tile][4].
2. Sign in to [Check Point Infinity Portal][5].
3. If you are not already in the **Harmony Email & Collaboration** Administrator Portal:
   - Click the **Menu** icon in the top-left corner.
   - In the **Harmony** section, click **Email & Collaboration**.
4. In the left-side menu, navigate to **Security Settings** > **Security Engines**.
5. Locate the **SIEM Integration** section and click **Configure**.
6. In the **Configure SIEM Integration** section, provide the following details:
   - **Transport**: Choose **HTTP Collector** from the dropdown.
   - **HTTP Collector URL**: Enter the endpoint URL that you generated in step 1.
   - **Format**: Choose **JSON** from the dropdown.
7. Click **Save**.

## Data Collected

### Logs

The Check Point Harmony Email & Collaboration integration collects and forwards security events to Datadog.

### Metrics

The Check Point Harmony Email & Collaboration integration does not include any metrics.

### Service Checks

The Check Point Harmony Email & Collaboration integration does not include any service checks.

### Events

The Check Point Harmony Email & Collaboration integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: https://www.checkpoint.com/harmony/email-security/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/help/
[4]: https://app.datadoghq.com/integrations/checkpoint_harmony_email_and_collaboration
[5]: https://portal.checkpoint.com/
