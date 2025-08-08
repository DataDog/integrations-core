# Anthropic Usage and Costs

## Overview

This integration provides Datadog users with comprehensive visibility into their Anthropic API usage and associated costs. By ingesting data from Anthropic's Admin usage and cost APIs, the integration enables organizations to:

- **Monitor LLM token consumption** (input, output, cache usage) in near real-time
- **Track costs by model, workspace, and service tier**, supporting accurate attribution and budgeting
- **Understand usage trends** across teams, API keys, or user identities to optimize model usage
- **Set up alerting and dashboards** that highlight anomalies in usage or unexpected cost spikes

This integration is especially valuable for teams using Anthropic at scale who want to manage spend, understand product adoption, and ensure efficient use of AI resources—all within the familiar Datadog observability platform.

## Setup

To get started with the Anthropic Admin API integration in Datadog, follow the steps below:

### 1. Generate an Admin API Key

You will need an [Admin API key][5] from Anthropic. This key allows access to usage and cost reports across your organization.

1. Navigate to your organization's settings or reach out to your Anthropic account admin to create a new Admin API key.
2. Copy the API key to a secure location.

### 2. Configure the Datadog Integration

1. In Datadog, go to [**Integrations > Anthropic**](https://app.datadoghq.com/integrations?integrationId=anthropic).
2. In the configuration panel, provide the **Admin API Key** by pasting the key you generated from Anthropic.
3. Click **Save Configuration**.

Once saved, Datadog will begin polling Anthropic usage and cost endpoints using this key and populate metrics in your environment.

## Data Collected

### Metrics

See [metadata.csv][4] for a list of metrics provided by this integration.

### Service Checks

Anthropic Usage and Costs does not include any service checks.

### Events

Anthropic Usage and Costs does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: https://www.anthropic.com/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/help/
[4]: https://github.com/DataDog/integrations-core/blob/master/anthropic_usage_and_costs/metadata.csv
[5]: https://docs.anthropic.com/en/api/administration-api

