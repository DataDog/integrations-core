# Mailchimp

## Overview

[Mailchimp][1] is an all-in-one marketing platform designed to help businesses create, send, and analyze email campaigns. It offers tools for audience management, marketing automation, and insights to boost engagement and grow your business. Businesses can design emails, manage subscribers, and track campaign performance.

This integration ingests the following metrics:

- Reports (metrics related to campaigns)
- Lists/audience (metrics related to audiences)

The Mailchimp integration collects metrics from campaigns and lists, directing them into Datadog for analysis. This integration provides insights including total campaigns, email performance, click-through rates, open rates, bounce rates, unsubscribes, and abuse reports. It features consolidated statistics for campaigns sent in the last 30 days, along with many additional metrics, all accessible through out-of-the-box dashboards.

## Setup

### Get API credentials for Mailchimp

1. Log in to your [Mailchimp account][2]. 
2. Check the url for the Server prefix. It is the `xxxx`part of the url(eg: `https://xxxx.admin.mailchimp.com/`).
3. Click on the profile icon and select Profile option.
4. Navigate to the **Extras** tab and click on **API keys** from the Dropdown.
5. Scroll down to the **Your API Keys** section and click **Create A Key**.
6. Enter your preferred name for the API key and click on **Generate Key**. Your API key is now generated.


### Add your Mailchimp Credentials

- Mailchimp Marketing API Key
- Mailchimp Server Prefix


## Data Collected

### Metrics

The Mailchimp integration collects and forwards campaign and list (audience) metrics to Datadog.

{{< get-metrics-from-git "mailchimp" >}}

### Service Checks

The Mailchimp integration does not include any service checks.

### Events

The Mailchimp integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: https://mailchimp.com/
[2]: https://login.mailchimp.com/
[3]: https://docs.datadoghq.com/help/
