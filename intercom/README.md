# Intercom

## Overview
[Intercom][1] is a customer communication platform that enables businesses to engage with their users through in-app messaging, email, and chat. It offers features like live chat, automated messaging, and customer support tools, making it easier for companies to provide personalized customer experiences.

The Intercom integration seamlessly collects  admin activities, data events, conversations, news items and tickets data and ingests them into Datadog for comprehensive analysis using webhooks.

## Setup

Follow the instructions below to configure this integration for your Intercom account.

### Configuration

#### Webhook Configuration
Configure the Datadog endpoint to forward Intercom events as logs to Datadog. See [Intercom webhook overview][3] for more details.

- #### Webhook URL generation
    - Select an existing API key or create a new one by clicking one of the buttons below:<!-- UI Component to be added by DataDog team -->
- #### Register a new application
    - Sign in to your [Intercom][2] account with a user which has full access to Apps and Integrations.
    - Go to **Settings**.
    - Under the Integrations section, select **Developer Hub**.
    - Click on **New app**
    - Fill in the required details for your application, such as the name and associated workspace.
    - Click **Create app**.
- #### Configure webhook topics
    - Select Required permissions
        - After creating the app, go to the *Authentication* section in the left-hand menu and click on the **Edit** button in the top-right corner.
        - By default, all permissions will be enabled, but ensure that the following permissions are specifically enabled:
            - Read admins
            - Read content data
            - Read conversations
            - Read events
            - Read tickets
        - Click **Save**
    - Select Webhook topics
        - Now, go to the Webhooks section present in the left sidebar.
        - Enter the endpoint URL that was generated [here](#webhook-url-generation).
        - From the dropdown menu labeled **Select a topic**, select the below webhook topics:
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
        - Click **Save**.

## Data Collected

### Logs

The Intercom integration collects and forwards admin activities, tickets, data events, news items and conversation logs to Datadog.

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