# Agent Check: Plaid

[Plaid](https://plaid.com/) specializes in financial technology by offering APIs that allow developers to integrate banking services into their applications. By connecting users' bank accounts to apps, Plaid enables features like account verification, transaction history retrieval, and balance checks. This functionality is crucial for various applications, including budgeting tools, personal finance management, and payment processing.

## Overview

Here are some insights that can be drawn from your Plaid dashboard:

- **Descriptive Trends**: Assess common descriptions for categorization.
- **Failure Patterns**: Investigate failure reasons to improve reliability.
- **Network Performance**: Evaluate network effectiveness and transaction success rates.
- **Status Monitoring**: Track overall transaction statuses for operational efficiency.
- **Sweep Trends**: Analyze sweep statuses to understand fund movement dynamics.
- **Type Classification**: Categorize transactions by type for deeper financial insights.
- **Currency Insights**: Examine iso_currency_code for multi-currency transaction patterns.

## Setup

1. Log in to [Plaid](https://dashboard.plaid.com/signin/).
2. Client ID and Secret can be obtained through this [link](https://dashboard.plaid.com/developers/keys).

### Configuration

Configure the Datadog endpoint to forward Plaid logs to Datadog.
1. Log in to [Plaid Dashboard](https://dashboard.plaid.com/)
2. In the left pane, go to the **Developers** section.
3. Expand the drop-down menu and select **Keys** 
4. Retrieve your `client_id` and `secret`.

#### To obtain Access Token, follow these steps:
1. [**Retrieve the `institution_id` from Plaid**](https://plaid.com/docs/api/institutions/#institutionsget) :  
    Use the Plaid API's **/institutions/get** endpoint to fetch the `institution_id`.
2. [**Create a Public Token**](https://plaid.com/docs/api/sandbox/#sandboxpublic_tokencreate):  
    Create a public token by using the `institution_id` that you retrieved from Step 1 and hit **/public_token/create** endpoint.
3. [**Obtain the Access token**](https://plaid.com/docs/api/items/#itempublic_tokenexchange):  
    Use the `public_token` you obtained from Step 2 to exchange it for an `access_token`. Send the `public_token` to the **/item/public_token/** exchange.
4. **Store the Access Token Securely**:  

| Plaid Parameters | Description |
|----------|----------|
| Client ID | Client of the Plaid account. |
| Secret | Secret of the Plaid account |
| Access Token | Access Token of the Plaid account |



## Data Collected

### Logs

The crawler collects Plaid logs, including Transfer events, Recurring Transfer events, Investment transactions, and Auth metrics. All sensitive data is removed before sending the logs to Datadog.

### Metrics

The Plaid integration does not include any metrics.

### Events

The Plaid integration does not include any events.

### Service checks

The Plaid integration does not include any service checks.


## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/help/

