## Overview

Mailgun is an API-based email delivery platform that allows you to:

- Build and manage large-scale email marketing applications.
- Send and track transactional messages.
- Remove invalid email addresses from your list.
- Improve your deliverability and drive higher conversion rates.

Integrate with Datadog to collect email delivery and engagement metrics and logs to track the performance of your Mailgun services.

## Setup

### Add and verify domain

1. Log in to your [Mailgun account][1].
2. In the sidebar on the left, click **Sending**. The menu expands. Select **Domains**.
3. Click **Add New Domain** at the top right.
4. Enter your Domain name and region and click **Add Domain**.
5. Verify your domain by following [the instructions in the Mailgun documentation][2].

### View Mailgun API key

When you sign up for Mailgun, a primary account API key is created for you.
This key allows you to perform all CRUD operations through our various API
endpoints and for any of your sending domains.

1. Log in to your [Mailgun account][1].
2. Click your name on the top right, and open the dropdown.
3. Click **API Keys**.
4. Click the eye icon next to **Private API Key**.

### Enable metrics collection

1. Navigate to the configuration tab inside the Datadog [Mailgun integration tile][3].
2. Enter your domain name and the region for your domain.
3. Paste in the API Key found in the steps above.
4. Optionally, add custom tags to associate tags with all metrics collected for this integration.

### Enable logs collection

You may configure Mailgun to forward events as logs to
Datadog. See the section **Tracking Messages - Webhooks** [in the Mailgun documentation][4] for more details.

1. Copy the generated URL from the instructions on the [Mailgun integration tile][3].
2. Log in to your Mailgun account.
3. Click **Sending** in the left side column.
4. Click **Webhooks** in the dropdown.
5. Click **Add webhook** in the top right corner.
6. Select the Event type you want to track.
7. Paste in the generated URL in step 1 under **URL**.
8. Click **Create Webhook**.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

### Logs

Mailgun events will show up as logs under the source `mailgun`.

### Events

The Mailgun integration does not include any events.

### Service Checks

The Mailgun integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][6].

[1]: https://login.mailgun.com/login/
[2]: https://help.mailgun.com/hc/en-us/articles/360026833053
[3]: /integrations/mailgun
[4]: https://documentation.mailgun.com/en/latest/user_manual.html#webhooks-1
[5]: https://github.com/DataDog/dogweb/blob/prod/integration/mailgun/mailgun_metadata.csv
[6]: https://docs.datadoghq.com/help
