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

**Minimum Agent version:** 7.58.2

## Setup

1. Log in to [Plaid](https://dashboard.plaid.com/signin/).
2. Client ID and Secret can be obtained through this [link](https://dashboard.plaid.com/developers/keys).

### Configuration

Configure the Datadog endpoint to forward Plaid logs to Datadog.
1. Log in to [Plaid Dashboard](https://dashboard.plaid.com/)
2. Navigate to the **Developers** section in the left pane.
3. Extend the drop-down menu and click on **Keys** 
4. Obtain the client_id and Secret.

#### To obtain Access Token, follow these steps:
   1. **Get institution_id from Plaid**:  
      Hit Plaid API **/institutions/get** endpoint to obtain institution_id. Reference [link](https://plaid.com/docs/api/institutions/#institutionsget) 
   2. **Create a Public Token**:  
      You will need to create a public token. Use the institution_id that you retrieved from Step 1 and hit **/public_token/create** endpoint. Reference  [link](https://plaid.com/docs/api/sandbox/#sandboxpublic_tokencreate) 
   3. **Obtain the Access token**:  
      Now, use the public_token you obtained from Step 2 to exchange it for an access_token. Send the public_token to this **/item/public_token/** exchange . Reference [link](https://plaid.com/docs/api/items/#itempublic_tokenexchange) 


   4. **Store the Access Token Securely**:  
      


| Plaid Parameters | Description |
|----------|----------|
| Plaid API URL | API URL of Plaid. | 
| Client ID | Client of the Plaid account. |
| Secret | Secret of the Plaid account |
| Access Token | Access Token of the Plaid account |



## Data Collected

The crawler will implement data collection of Plaid logs for the List of Transfer events, Recurring Transfer events, Investment transactions
events and Auth metrics. Sensitive data are removed and sent to Datadog.


## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: **LINK_TO_INTEGRATION_SITE**
[2]: /account/settings/agent/latest
[3]: https://docs.datadoghq.com/help/

