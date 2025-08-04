# Agent Check: Anthropic Usage and Costs

## Overview

This integration provides Datadog users with comprehensive visibility into their Anthropic API usage and associated costs. By ingesting data from Anthropic's Admin usage and cost APIs, the integration enables organizations to:

- **Monitor LLM token consumption** (input, output, cache usage) in near real-time
- **Track costs by model, workspace, and service tier**, supporting accurate attribution and budgeting
- **Understand usage trends** across teams, API keys, or user identities to optimize model usage
- **Set up alerting and dashboards** that highlight anomalies in usage or unexpected cost spikes

This is especially valuable for teams using Anthropic at scale who want to manage spend, understand product adoption, and ensure efficient use of AI resources - all within the familiar Datadog observability platform.

## Setup

To get started with the Anthropic Admin API integration in Datadog, follow the steps below:

### 1. Generate an Admin API Key

You will need an **Admin API key** from Anthropic. This key allows access to usage and cost reports across your organization.

1. Visit the [Anthropic Admin API documentation](https://docs.anthropic.com/en/docs/admin-api-overview).
2. Navigate to your organization's settings or reach out to your Anthropic account admin.
3. Create a new Admin API key with appropriate permissions for accessing:
   - `GET /v1/organizations/usage_report/messages`
   - `GET /v1/organizations/cost_report`
4. **Copy the API key** to a secure location.

### 2. Configure the Datadog Integration

1. In Datadog, go to **Integrations -> Anthropic**.
2. In the configuration panel, provide the **Admin API Key** by pasting the key you generated from Anthropic.
3. Click **Save Configuration**.

Once saved, Datadog will begin polling Anthropic usage and cost endpoints using this key and populate metrics in your environment.


## Data Collected

### Metrics

Anthropic Usage and Costs does not include any metrics.

### Service Checks

Anthropic Usage and Costs does not include any service checks.

### Events

Anthropic Usage and Costs does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/help/

