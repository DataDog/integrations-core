# Adyen

## Overview
[Adyen][1] is a global payment platform that provides a comprehensive suite of payment solutions for businesses. It enables companies to accept payments across online, mobile, and in-store channels. Adyen supports a wide range of payment methods, including credit cards, mobile wallets, and local payment options, and offers services such as fraud prevention and risk management.

The Adyen integration seamlessly collect the data of transactions, disputes, and payouts using the Adyen webhook capability and ingests them into Datadog for comprehensive analysis.

## Setup

Follow the instructions below to configure this integration for your Adyen account.

### Configuration

#### Webhook Configuration
Configure the Datadog endpoint to forward Adyen events as logs to Datadog. See [Adyen webhook overview][2] for more details.

- #### Webhook URL generation
    - Select an existing API key or create a new one by clicking one of the buttons below:<!-- UI Component to be added by DataDog team -->
- #### Register a new Webhook
    1. Sign in to your [Adyen][1] account with a user which has a **Merchant technical integrator** role along with default roles, and has access to **Company account and all associated merchant accounts**.
    2. Under the **Developers** section, click **Webhooks**.
    3. Click on **Create new webhook**.
    4. In the Recommended Webhooks section, select the **Add** option located next to the **Standard Webhook**.
    5. Under **General**, configure the following:

        | Setting                                                 | Description                                                                             |
        |------------------------------                                          |-----------------------------------------------------------------------------------------|
        | Version                                  | Select webhook version 1                                                          |
        | Description      | Add appropriate description to a webhook                                           |
        | Merchant accounts  | Keep all merchant accounts or select the merchant account for which data needs to be ingested into Datadog                                       |
    
    6. Under **Server configuration**, configure the following:

        | Setting                                                 | Description                                                                             |
        |------------------------------                                          |-----------------------------------------------------------------------------------------|
        | URL                                  | Enter the endpoint URL that you generated [here](#webhook-url-generation).                                                          |
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