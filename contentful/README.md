## Overview

[Contentful][1] is a content (articles, photos, and videos) management platform that allows businesses to create, manage, and deliver digital content across various channels like websites and mobile apps through its intuitive interface and robust APIs or SDKs.

Integrate with Datadog to gain insights into Contentful activities related to content and other actions as part of your Contenful spaces and environments.

## Setup

Follow the instructions below to configure this integration for your Contentful space.

### Configuration

#### Webhook Configuration
Configure the Datadog endpoint to forward Contentful events as logs to Datadog. See [Contentful Webhook overview][2] for more details.

1. Select an existing API key or create a new one by clicking one of the buttons below:<!-- UI Component to be added by DataDog team -->
2. Log in to your [Contenful account][3] as space admin.
3. Go to **Settings > Webhooks**.
4. Click on **Add Webhook**.
5. Add name and webhook URL generated from step 1.
6. Ensure `POST` method is selected under **URL** and `Active` button is true.
7. Select the type of Content and Action events which you want to be pushed into Datadog.
8. Configure filters to trigger webhook for specific entities if required.
9. Select `application/json` under **Content type**.
10. Select `Customize the webhook payload` under **Payload** section and paste below json in the input:
```
{
  "event": "{ /topic }",
  "user": "{ /user/sys/id }",
  "details": "{ /payload }"
}
```
11. Click on **Save**.

## Data Collected

### Logs
The Contentful integration ingests the following logs:
- Content events related to Entries, Assets and Content Types.
- Action events related to Scheduled Actions and Bulk Actions.
- Other events related to Tasks and Comments.

### Metrics

The Contentful integration does not include any metrics.

### Events

The Contentful integration does not include any events.

### Service Checks

The Contentful integration does not include any service checks.

## Support

Need help? Contact [Datadog support][4].


[1]: https://www.contentful.com/products/platform/
[2]: https://www.contentful.com/developers/docs/webhooks/overview/
[3]: https://be.contentful.com/login/
[4]: https://docs.datadoghq.com/help/
