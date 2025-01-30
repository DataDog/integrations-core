# Intercom

## Overview
[Intercom][1] is a customer communication platform that enables businesses to engage with their users through in-app messaging, email, and chat. It offers features like live chat, automated messaging, and customer support tools, making it easier for companies to provide personalized customer experiences.

The Intercom integration seamlessly collects admin activities, data events, conversations, news items, and ticket data, and ingests them into Datadog for comprehensive analysis using [webhooks][6].

## Setup

Follow the instructions below to configure this integration for your Intercom account.

### Configuration

#### Webhook Configuration
Configure the Datadog endpoint to forward Intercom events as logs to Datadog. See [Intercom webhook overview][3] for more details.

    1. Copy the generated URL inside the **Configuration** tab on the Datadog [Intercom integration tile][4].
    2. Sign in to your [Intercom][2] account using a user account with full access to Apps and Integrations.
    3. Go to **Settings**.
    4. In the Integrations section, select **Developer Hub**.
    5. Click **New app**.
    6. Fill in the required details for your application, including the name and associated workspace.
    7. Click **Create app**.
- #### Configure webhook topics
    1. Select Required permissions
        1. After creating the app, go to the *Authentication* section in the left-side menu, and click the **Edit** button in the top-right corner.
        2. By default, all permissions are enabled. However, ensure that the following specific permissions are enabled:
            - Read admins
            - Read content data
            - Read conversations
            - Read events
            - Read tickets
        3. Click **Save**.
    2. Select Webhook topics
    ```
        1. Next, navigate to the **Webhooks** section using the left-side menu.
        2. Enter the endpoint URL that you generated in step 1 of [Webhook Configuration](#webhook-configuration).
        3. On the **Select a topic** dropdown menu, select the following webhook topics:
            - admin.activity_log_event.created
            - content_stat.news_item
            - conversation.admin.closed
            - conversation.admin.replied
            - conversation.admin.single.created
            - conversation.admin.snoozed
            - conversation.admin.unsnoozed
            - conversation.priority.updated
            - conversation.rating.added
            - conversation.user.created
            - event.created
            - ticket.admin.assigned
            - ticket.attribute.updated
            - ticket.created
            - ticket.state.updated
            - ticket.team.assigned
        4. Click **Save**.

## Data Collected

### Logs

The Intercom integration collects and forwards admin activities, tickets, data events, news items, and conversation logs to Datadog.

### Metrics

The Intercom integration does not include any metrics.

### Events

The Intercom integration does not include any events.

### Service Checks

The Intercom integration does not include any service checks.

## Support

For further assistance, contact [Datadog Support][5].

[1]: https://www.intercom.com/
[2]: https://app.intercom.com/
[3]: https://developers.intercom.com/docs/webhooks
[4]: https://app.datadoghq.com/integrations/intercom
[5]: https://docs.datadoghq.com/help/
[6]: https://developers.intercom.com/docs/references/2.10/webhooks/webhook-models