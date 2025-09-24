# Anthropic Usage and Costs

## Overview

Datadog's Anthropic Usage and Costs integration allows you to get visibility into your Anthropic usage and associated costs. By ingesting data from Anthropic's newly released Admin usage and cost API, this integration enables your teams to:

- **Monitor LLM token consumption** (input, output, cache usage) in near real-time
- **Track costs** by model, workspace, and service tier, supporting accurate attribution and budgeting
- **Understand usage trends** across teams, API keys, or users to optimize model usage
- **Set up alerting and dashboards** that highlight anomalies in usage or unexpected cost spikes

This integration is especially valuable for teams using Anthropic at scale who want to manage spend, understand product adoption, and ensure efficient use of AI resources-all within Datadog. With this data you will be able to introduce and validate optimization strategies to get the best out of Anthropic.

You can also see your Anthropic costs in Datadog [Cloud Cost Management][6], allowing you to answer key questions: Which models or workspaces are generating the most cost? Are workloads using the right service tier (Standard, Batch, or Priority)? Are teams effectively using caching or ephemeral sessions? What's the cost breakdown between Claude Opus and Claude Sonnet?

**Minimum Agent version:** 7.69.0

## Setup

To get started with the Anthropic Admin API integration in Datadog, follow the steps below:

### 1. Generate an Admin API Key

You will need an [Admin API key][5] from Anthropic. This key allows access to usage and cost reports across your organization.

1. Navigate to your organization's settings or reach out to your Anthropic account admin to create a new Admin API key.
2. Copy the API key to a secure location.

### 2. Configure the Datadog Integration

1. In Datadog, go to [**Integrations > Anthropic Usage and Costs**](https://app.datadoghq.com/integrations?integrationId=anthropic-usage-and-costs).
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
[6]: /cost
