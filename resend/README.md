# Resend

## Overview

[Resend][1] is an email delivery service for sending broadcast and transactional emails via a developer API.

To gain insights into Resend's broadcast and transactional message streams, integrate Resend with Datadog using [webhooks][2].
This allows events to be received by Datadog and converted to logs.

## Setup

Follow the instructions below to configure this integration for your Resend account.


### Configuration

#### Webhook configuration steps
Create a webhook in Resend to forward events to Datadog:
1. Log into your [Resend account][3] and navigate to the [webhooks][4] page.
2. Click the **Add webhook** button and enter the following:
   - Enter the url provided by Datadog.
   - Select "All Events" for the events types.
3. Click **Add**.

#### Optional: Enable click tracking for each Resend domain
Follow these steps to enable email click and optionally open email tracking for each Resend domain:
1. Navigate to the Resend [domains][5] page.
3. For each sending domain in use:
   1. Click on the domain name to edit.
   2. In the Configuration section, enable **Click Tracking**.
   3. Optionally, enable **Open Tracking**. Though Resend [cautions against depending on open tracking](https://resend.com/docs/knowledge-base/why-are-my-open-rates-not-accurate).

#### Optional: Surface the use of tags in transactional email in the Datadog Dashboard
The Resend API supports per-message tags for transactional email, such as a 
`priority` attribute with values of _high_, _normal_, or _low_. The tag can be 
defined as a template variable in the Datadog dashboard to filter results by tag value. 
For an example, see the `priority` template variable in the Resend Overview dashboard provided with this integration.

## Data Collected

### Logs
The Resend integration converts Resend webhook events to Datadog logs. The events
contain email header and tag information which included sender and recipient email addresses.
Actual email content is not included in the events.

### Metrics
The Resend integration does not define any metrics.

### Service Checks
Resend does not include any service checks.

### Events
Resend does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][6].

[1]: https://resend.com/
[2]: https://resend.com/docs/dashboard/webhooks/introduction
[3]: https://resend.com/login
[4]: https://resend.com/webhooks
[5]: https://resend.com/domains
[6]: https://docs.datadoghq.com/help/
