# Postmark

## Overview

[Postmark][1] is an email delivery service for sending and tracking application emails. It offers a scalable alternative to traditional SMTP and provides essential metrics like sent, opened, bounced, and spam complaint rates. This enables efficient email management and monitoring.

To gain insights into Postmark's broadcast and transactional message streams, integrate Postmark with Datadog using [webhooks][2].

## Setup

Follow the instructions below to configure this integration for your Postmark account.


### Configuration

#### Enable open and link tracking in server settings for the message streams
Follow these steps to enable both features:

1. Log into your [Postmark account][3]. This redirects you to the [servers][4] page.
2. Select the desired server. This redirects you to the **Message Streams** page.
3. In the navigation panel, click the **Settings** tab.
4. In the **Tracking** section, enable both **Open tracking** and **Link tracking**.

#### Webhook configuration steps
Configure the Datadog endpoint to forward the following activity logs to Datadog:
- **Broadcast** message streams
- **Transactional** message streams

See [Postmark Webhook Overview][2] for more details.

Perform the following steps to configure the webhook for both of the message streams mentioned above.

1. Select an existing API key or create a new one by clicking one of the buttons below:<!-- UI Component to be added by DataDog team -->
2. Log in to your [Postmark account][3]. This redirects you to the [servers][4] page.
3. Select the desired server. This redirects you to the **Message Streams** page.
4. On the message streams page, select an existing broadcast or transactional message stream or create a new one. 
   - To create a new **Broadcasts** stream: <br/> 
   Click the **Create Message Stream** button, enter a stream name, and select **Broadcasts** as the message type. <br/> **OR**
   - To create a new **Transactional** stream: <br/> 
   Click the **Create Message Stream** button, enter a stream name, and select **Transactional** as the message type.
5. In the navigation panel, click the **Webhooks** tab.
6. Click **Add Webhook**.
7. Enter the webhook URL provided from step 1.
8. Choose the types of events you want to push to Datadog.
9. Click **Save webhook**.

## Data Collected

### Logs
The Postmark integration forwards the Postmark message streams activity logs to Datadog.

### Metrics
Postmark does not include any metrics.

### Service Checks
Postmark does not include any service checks.

### Events
Postmark does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][5].

[1]: https://postmarkapp.com/
[2]: https://postmarkapp.com/developer/webhooks/webhooks-overview
[3]: https://account.postmarkapp.com/login
[4]: https://account.postmarkapp.com/servers
[5]: https://docs.datadoghq.com/help/
