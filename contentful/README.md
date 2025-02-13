# Contentful

## Overview

[Contentful][1] is a content (articles, photos, and videos) management platform that allows businesses to create, manage, and deliver digital content across various channels like websites and mobile apps through its intuitive interface and robust APIs or SDKs.

Integrate with Datadog to gain insights into Contentful activities related to content and other actions as part of your Contentful spaces and environments.

## Setup

Follow the instructions below to configure this integration for your Contentful space.

### Configuration

#### Webhook Configuration
Configure the Datadog endpoint to forward Contentful events as logs to Datadog. See [Contentful Webhook overview][2] for more details.

1. Copy the generated URL inside the **Configuration** tab on the Datadog [Contentful integration tile][5].
2. Log in to your [Contentful account][3] as space admin.
3. Go to **Settings > Webhooks**.
4. Click on **Add Webhook**.
5. Add a name and fill in the webhook URL that you generated in step 1.
6. For **URL**, select the `POST` method, and for **Active**, select true.
7. Select the type of **Content** and **Action** events that you want to push to Datadog.
8. Configure filters to trigger the webhook for specific entities if required.
9. Under **Content type**, select `application/json`.
10. Under **Payload**, select `Customize the webhook payload`, then paste the following into the input field:
    ```
    {
      "event": "{ /topic }",
      "user": "{ /user/sys/id }",
      "details": "{ /payload }"
    }
    ```
11. Click **Save**.

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
[5]: https://app.datadoghq.com/integrations/contentful
