# Brevo

## Overview

[Brevo][1] is a cloud-based digital marketing platform designed for creating, sending, and tracking email campaigns, transactional emails, and more. It offers tools for automation and analytics, helping businesses optimize their email marketing strategies and monitor performance.

Integrate Brevo with Datadog to gain insights into Brevo marketing campaign emails and track Brevo performance based on events and other transactional events using [webhooks][2].

## Setup

Follow the instructions below to configure this integration for Brevo Marketing and Transactional events through a Webhook.

### Configuration

#### Webhook configuration for marketing events
Configure the Datadog endpoint to forward Brevo marketing events as logs to Datadog. For more details, see the Brevo [Marketing webhooks][3] documentation.

1. Select an existing API key or create a new one by clicking one of the buttons below:
2. Log in to your [Brevo account][4].
3. In the left-side panel, navigate to **Campaigns**.
4. Navigate to the **Settings** Page.
5. Under the **Webhooks** section, click **Configure**.
6. Click **Add a New Webhook**.
7. Enter the webhook URL that you identified previously.
8. Choose the types of messages and contact logs you want to forward to Datadog.
9. Click **Add**.

#### Webhook configuration for transactional events
Configure the Datadog endpoint to forward Brevo transactional events as logs to Datadog. For more details, see the Brevo [Transactional webhooks][5] documentation.

1. Select an existing API key or create a new one by clicking one of the buttons below:
2. Log in to your [Brevo account][4]. If you are already logged in, Brevo automatically redirects to the [Brevo homepage][6].
3. In the left-side panel, navigate to **Transactional**.
4. In **Settings**, click "**Webhook**".
5. Click **Add a new webhook**.
6. Enter the webhook URL that you identified previously.
7. Select the types of message logs to forward to Datadog.
8. Click **Save**.

## Data Collected

### Logs
The Brevo integration forwards the marketing and transactional event logs to Datadog.

### Metrics
Brevo does not include any metrics.

### Service Checks
Brevo does not include any service checks.

### Events
Brevo does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: https://www.brevo.com/products/marketing-platform/
[2]: https://developers.brevo.com/docs/how-to-use-webhooks
[3]: https://developers.brevo.com/docs/marketing-webhooks
[4]: https://login.brevo.com/
[5]: https://developers.brevo.com/docs/transactional-webhooks
[6]: https://app.brevo.com/
[7]: https://docs.datadoghq.com/help/
