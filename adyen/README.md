# Adyen

## Overview
[Adyen][1] is a global payment platform that provides a comprehensive suite of payment solutions for businesses. It enables companies to accept payments online, on mobile, and in-store. Adyen supports a wide range of payment methods, including credit cards, mobile wallets, and local payment options, and offers services such as fraud prevention and risk management.

The Adyen integration collects transaction, dispute, and payout data using Adyen's webhook capability and ingests it into Datadog for comprehensive analysis.

## Setup

Follow the instructions below to configure this integration for your Adyen account.

### Webhook configuration

Configure the Datadog endpoint to forward Adyen events as logs to Datadog. For more details, see [Adyen webhook overview][2].

1. **Generate a webhook URL**: Select an existing API key or create a new one by clicking one of the buttons below:<!-- UI Component to be added by DataDog team -->
2. **Register a new webhook**: 
    1. Sign in to your [Adyen][1] account using a user with the **Merchant technical integrator** role, along with default roles, who has access to the **Company account and all associated merchant accounts**.
    2. Under the **Developers** section, click **Webhooks**.
    3. Click **Create new webhook**.
    4. In the **Recommended Webhooks** section, click **Add** next to **Standard Webhook**.
    5. Under **General**, configure the following:

        | Setting                                                 | Configuration                                                                             |
        |------------------------------                                          |-----------------------------------------------------------------------------------------|
        | Version                                  | Select webhook version 1                                                          |
        | Description      | Add a description to the webhook                                           |
        | Merchant accounts  | Choose whether to keep all merchant accounts or select specific accounts for which data needs to be ingested into Datadog                                       |
    
    6. Under **Server configuration**, configure the following:

        | Setting                                                 | Configuration                                                                             |
        |------------------------------                                          |-----------------------------------------------------------------------------------------|
        | URL                                  | Enter the endpoint URL that you generated in step 1 of [Webhook configuration](#webhook-configuration).                                                          |
        | Method      | JSON                                           |
        | Encryption protocol  | TLSv1.3                                       |
    7. Under **Events**, keep the default selected events as per **Standard Webhook**.
    8. Click **Save configuration**.


## Data Collected

### Logs

The Adyen integration collects and forwards transaction, dispute, and payout logs to Datadog.

### Metrics

The Adyen integration does not include any metrics.

### Events

The Adyen integration does not include any events.

### Service Checks

The Adyen integration does not include any service checks.

## Support

For further assistance, contact [Datadog Support][3].

[1]: https://www.adyen.com/
[2]: https://docs.adyen.com/development-resources/webhooks/
[3]: https://docs.datadoghq.com/help/