# Plivo

## Overview
[Plivo][1] is a communication platform as a service provider that offers a range of communication APIs and tools for businesses. Plivo offers a comprehensive suite of communication services including SMS, messaging, and WhatsApp integrations. It also includes voice calling feature integrations, allowing businesses to make and receive voice calls through their platform, with support for multiparty and conference calls. Plivo provides a versatile communication platform to enhance customer engagement and streamline communication strategies.

The Plivo integration seamlessly collects message (SMS, MMS, and WhatsApp) and voice call data, and sends it to Datadog for comprehensive analysis.

## Setup

### Generate API credentials in Plivo

#### Plivo Auth ID and Auth Token

1. Sign in to [Plivo][2] using an Owner, Admin or Developer account.
2. Navigate to the **Overview** section.
3. In the **Account** section, get the **Auth ID** and **Auth Token** values.

      If you need to generate a new Auth Token, go to **Settings** > **Credentials**, then click **Generate Auth Token**.

#### Plivo subaccount Auth ID and Auth Token (optional)

You can use the credentials of a Plivo subaccount to retrieve data specific to that subaccount, rather than the entire account.

1. Sign in to [Plivo][2] using an Owner, Admin or Developer account.
2. Navigate to **Account** > **Settings** > **Subaccounts**.
3. Get the **Auth ID** and **Auth Token** of the subaccount that you want to use.

### Message Expiry Time (Optional)

- Set the "message expiry time" parameter in seconds in Datadog to match the message expiry time configured in Plivo. Ensure the expiry time remains synchronized with the configuration in Plivo to avoid fetching unsettled messages. The default value is 3 hours (10,800 seconds). Message ingestion into Datadog will be delayed by this duration to ensure only settled messages are fetched. Settled messages are fully processed and finalized, while unsettled messages are still in the queue. See [Message Expiry][4] to learn more.

### Connect your Plivo Account to Datadog

1. Add your Auth ID, Auth Token and Message Expiry Time

| Parameters                             | Description                                                  |
| -------------------------------------- | ------------------------------------------------------------ |
| Plivo Auth ID                          | The Auth ID of your plivo account.                           |
| Plivo Auth Token                       | The Auth Token of your plivo account.                        |
| Plivo Message Expiry Time (Optional)   | The Message Expiry Time (in seconds) for your Plivo account. Refer [here](#message-expiry-time-optional) for details.|

2. Click the Save button to save your settings.

## Data Collected

### Logs

The Plivo integration collects and forwards Messages(SMS, MMS, WhatsApp) and Voice call logs to Datadog.

### Metrics

The Plivo integration does not include any metrics.

### Events

The Plivo integration does not include any events.

### Service Checks

The Plivo integration does not include any service checks.

## Support

For further assistance, contact [Datadog Support][3].

[1]: https://www.plivo.com/
[2]: https://console.plivo.com/
[3]: https://docs.datadoghq.com/help/
[4]: https://support.plivo.com/hc/en-us/articles/14814454609561-Message-Expiry