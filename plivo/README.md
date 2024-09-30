# Plivo

## Overview
[Plivo][1] is a communication platform as a service provider that offers a comprehensive suite of communication APIs and tools for businesses. Notable aspects of Plivo product lineup include robust SMS, MMS, and WhatsApp services, enabling versatile and efficient messaging capabilities. These services are designed to enhance customer engagement and streamline communication strategies, making Plivo a valuable asset for businesses seeking to improve their communication workflows.

The Plivo integration seamlessly collects SMS, MMS, and WhatsApp services data and ingests it into Datadog for comprehensive analysis.

## Setup

### Plivo Datadog Integration Configuration

Configure the Datadog endpoint to forward Plivo logs to Datadog.

#### Plivo Auth ID and Auth Token

1. Sign in to [Plivo][2] using a user account with Owner, Admin or Developer role.
2. Navigate to the **Overview** section.
3. You can find the **Auth ID** and **Auth Token** under the *Account* section.
4. Copy these credentials for the following configuration steps. Ensure they are stored securely and not exposed in public repositories or insecure locations.
5. You can also generate the new **Auth Token**, refer [here](#generate-new-auth-token).

**Note**: If you are using the credentials of a Plivo subaccount, the data retrieved will be specific to that subaccount and not the entire account. To fetch the credentials of a particular subaccount, refer [here](#plivo-sub-account-auth-id-and-auth-token).

#### Generate new Auth Token 
- Navigate to **Account** > **Settings** > **Credentials**.
- Click on **Generate Auth Token**

#### Plivo Sub-Account Auth ID and Auth Token

- Sign in to [Plivo][2] using a user account with Owner, Admin or Developer role.
- Go to **Account** > **Settings** > **Subaccounts**.
- You can find the **Auth ID** and **Auth Token** of the subaccount for which you want the data to be ingested.

#### Message Expiry Time (Optional)

- Set the message expiry time in seconds to match the message expiry time configured in Plivo. Ensure that the expiry time remains synchronized with what is configured in Plivo. The default value is set to 3 hours (10800 seconds). Messages ingestion to Datadog will be delayed by this duration to ensure settled messages are fetched. Refer [here][4] to know more about Plivo message expiry.

**Note**: It is important to keep the Message Expiry Time in sync with the configured in Plivo; otherwise, unsettled message logs may be ingested.

## Data Collected

### Logs

The Plivo integration collects and forwards SMS, MMS and WhatsApp logs to Datadog.

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