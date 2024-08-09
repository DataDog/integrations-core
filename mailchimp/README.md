# Mailchimp

## Overview

[Mailchimp][1] is an all-in-one marketing platform designed to help businesses create, send, and analyze email campaigns. It offers tools for audience management, marketing automation, and insights to boost engagement and grow your business. With its user-friendly interface, businesses can easily design emails, manage subscribers, and track campaign performance.

This integration ingests the following Metrics:

- Reports (Metrics related to Campaigns)
- Lists/Audience (Metrics related to Audiences)

The Mailchimp integration seamlessly collects metrics from campaigns and lists, directing them into Datadog for analysis. This integration provides insights including total campaigns, email performance, click-through rates, open rates, bounce rates, unsubscriptions, and abuse reports. It features consolidated statistics for campaigns sent in the last 30 days, along with many additional metrics, all accessible through out-of-the-box dashboards.

## Setup

### Configuration

#### Get API Credentials of Mailchimp

1. Login to [Mailchimp account][2] and click on the profile icon.
2. Navigate to the **Extras** tab dropdown
3. Click on **API keys**
4. Scroll down to the **Your API Keys** section and click on **Create A Key**
5. Enter your preferred name for the API Key and Click **Ok**
6. Once the API Key is generated, copy and save it as you will only see it once.


#### Mailchimp DataDog Integration Configuration

Configure the Datadog endpoint to forward  Mailchimp metrics to Datadog.

1. Navigate to `Mailchimp`.
2. Add your Mailchimp credentials.

| Mailchimp Parameters | Description  |
| -------------------- | ------------ |
| Marketing API Key    | API key for your Mailchimp marketing account.  |
| Server Prefix        | Server Prefix (Ex. us13) of the Mailchimp account. It is the `xxxx` part of `https://xxxx.admin.mailchimp.com/`.   |

## Data Collected

### Metrics

The Mailchimp integration collects and forwards Campaigns and Lists(Audiences) metrics to Datadog.

### Service Checks

The Mailchimp integration does not include any service checks.

### Events

The Mailchimp integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: https://mailchimp.com/
[2]: https://login.mailchimp.com/
[3]: https://docs.datadoghq.com/help/
