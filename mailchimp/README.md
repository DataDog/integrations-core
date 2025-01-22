# Mailchimp

## Overview

[Mailchimp][1] is an all-in-one marketing platform designed to help businesses create, send, and analyze email campaigns. It offers tools for audience management, marketing automation, and insights to boost engagement and grow your business. Businesses can design emails, manage subscribers, and track campaign performance.

This integration ingests the following metrics:

- Reports (metrics related to campaigns)
- Lists/audience (metrics related to audiences)

The Mailchimp integration collects metrics from campaigns and lists, directing them into Datadog for analysis. This integration provides insights including total campaigns, email performance, click-through rates, open rates, bounce rates, unsubscribes, and abuse reports. It features consolidated statistics for campaigns sent in the last 30 days, along with many additional metrics, all accessible through out-of-the-box dashboards.

## Setup

### Configuration

#### Get API credentials for Mailchimp

1. Log in to your [Mailchimp account][2] and click the profile icon
2. Navigate to the **Extras** tab
3. Click **API keys**
4. Scroll down to the **Your API Keys** section and click **Create A Key**
5. Enter your preferred name for the API key and click **Ok**
6. Once the API key is generated, copy and save it as you will only see it once


#### Mailchimp DataDog integration configuration

Configure the Datadog endpoint to forward  Mailchimp metrics to Datadog.

1. Navigate to the `Mailchimp` integration tile in Datadog.
2. Add your Mailchimp credentials.

| Mailchimp parameters | Description  |
| -------------------- | ------------ |
| Marketing API key    | API key for your Mailchimp marketing account.  |
| Server prefix        | Server prefix (for example: us13) of the Mailchimp account. It is the `xxxx` part of `https://xxxx.admin.mailchimp.com/`.   |

## Data Collected

### Metrics

The Mailchimp integration collects and forwards campaign and list (audience) metrics to Datadog.

### Service Checks

The Mailchimp integration does not include any service checks.

### Events

The Mailchimp integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: https://mailchimp.com/
[2]: https://login.mailchimp.com/
[3]: https://docs.datadoghq.com/help/
