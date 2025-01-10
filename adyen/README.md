# Adyen

## Overview
[Adyen][1] is a global payment platform that provides a comprehensive suite of payment solutions for businesses. It enables companies to accept payments online, on mobile, and in-store. Adyen supports a wide range of payment methods, including credit cards, mobile wallets, and local payment options, and offers services such as fraud prevention and risk management.

The Adyen integration collects transaction, dispute, and payout data using Adyen's webhook capability and ingests it into Datadog for comprehensive analysis.

## Setup

Follow the instructions below to configure this integration for your Adyen account.

### Configuration

#### Webhook Configuration
Configure the Datadog endpoint to forward Adyen events as logs to Datadog. For more details, see [Adyen webhook overview][2].

    1. Copy the generated URL inside the **Configuration** tab on the Datadog [Adyen integration tile][4].
    2. Sign in to your [Adyen][1] account with a user which has a **Merchant technical integrator** role along with default roles, and has access to **Company account and all associated merchant accounts**.
    3. Under the **Developers** section, click **Webhooks**.
    4. Click on **Create new webhook**.
    5. In the Recommended Webhooks section, select the **Add** option located next to the **Standard Webhook**.
    6. Under **General**, configure the following:

        | Setting                                                 | Configuration                                                                             |
        |------------------------------                                          |-----------------------------------------------------------------------------------------|
        | Version                                  | Select webhook version 1                                                          |
        | Description      | Add a description to the webhook                                           |
        | Merchant accounts  | Choose whether to keep all merchant accounts or select specific accounts for which data needs to be ingested into Datadog                                       |
    
    7. Under **Server configuration**, configure the following:

        | Setting                                                 | Configuration                                                                             |
        |------------------------------                                          |-----------------------------------------------------------------------------------------|
        | URL                                  | Enter the endpoint URL that you generated in step 1 of [Webhook configuration](#webhook-configuration).                                                          |
        | Method      | JSON                                           |
        | Encryption protocol  | TLSv1.3                                       |
    8. Under **Events**, keep the default selected events as per **Standard Webhook**.
    9. Click **Save configuration**.


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
[4]: https://app.datadoghq.com/integrations/adyen