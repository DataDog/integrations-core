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
1. Navigate to Plaid.
2. Add your Plaid credentials.

| Plaid Parameters | Description |
|----------|----------|
| Client ID | Client of the Plaid account. |
| Secret | Secret of the Plaid account |


## Data Collected

The crawler will implement data collection of Plaid logs for the List of Transfer events, remove sensitive data and send it to Datadog.


## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/help/

