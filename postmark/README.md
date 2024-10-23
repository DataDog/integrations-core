## Overview

[Postmark][1] is an email delivery service for sending and tracking application emails, offering a scalable alternative to traditional SMTP. It provides essential metrics, including sent, opened, bounced, and spam complaint rates, enabling effective email management and monitoring.

Integrate Postmark with Datadog to gain insights into Postmark broadcast and transactional message streams activity logs using [webhooks][2].

## Setup

Follow the instructions below to configure this integration for Postmark broadcast and transactional message streams activity logs through a webhook.

### Configuration
#### Enable open and link tracking in server settings for the message streams
Follow these steps to enable both features:

1. Log in to your [Postmark account][3]; this will redirect you to the [servers page][4].
2. Select the desired server; this will redirect you to the **Message Streams page**.
3. In the navigation panel, click on **Settings** tab.
4. In the Tracking section, enable both **Open tracking** and **Link tracking**.

#### Webhook configuration steps for broadcast message streams
Configure the Datadog endpoint to forward Postmark broadcast message streams activity logs to Datadog.

1. Select an existing API key or create a new one by clicking one of the buttons below:<!-- UI Component to be added by DataDog team -->
2. Log in to your [Postmark account][3]; this will redirect you to the [servers page][4].
3. Select the desired server; this will redirect you to the **Message Streams page**.
4. In the message streams page, select an existing broadcast message stream or create a new one by clicking the **Create Message Stream** button (enter a stream name and select the message type as **Broadcasts**).
5. In the navigation panel, click on **Webhooks** tab.
6. Click on the **Add Webhook** button.
7. Enter the webhook URL provided from step 1.
8. Choose the types of events you want to push to DataDog.
9. Click **Save webhook**.


#### Webhook configuration steps for transactional message streams
Configure the Datadog endpoint to forward Postmark transactional message streams activity logs to Datadog.

1. Select an existing API key or create a new one by clicking one of the buttons below:<!-- UI Component to be added by DataDog team -->
2. Log in to your [Postmark account][3]; this will redirect you to the [servers page][4].
3. Select the desired server; this will redirect you to the **Message Streams page**.
4. In the message streams page, select an existing transactional message stream or create a new one by clicking the **Create Message Stream** button (enter a stream name and select the message type as **Transactional**).
5. In the navigation panel, click on **Webhooks** tab.
6. Click on the **Add Webhook** button.
7. Enter the webhook URL provided from step 1.
8. Choose the types of events you want to push to DataDog.
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
