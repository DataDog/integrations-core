# Anthropic Usage and Costs

## Overview

Datadog's Anthropic Usage and Costs integration allows you to get visibility into your Anthropic usage and associated costs. By ingesting data from Anthropic's Admin and Analytics usage and cost APIs, this integration enables your teams to:

- **Monitor LLM token consumption** (input, output, cache usage) in near real-time
- **Track costs** by model, workspace, and service tier, supporting accurate attribution and budgeting
- **Attribute usage and spend to individual users** (Enterprise plans): break down token consumption and dollar cost by user, product (API, Claude Code, Claude.ai), context window, inference geography, and speed
- **Understand usage trends** across teams, API keys, or users to optimize model usage
- **Set up alerting and dashboards** that highlight anomalies in usage or unexpected cost spikes

This integration is especially valuable for teams using Anthropic at scale who want to manage spend, understand product adoption, and ensure efficient use of AI resources-all within Datadog. With this data you will be able to introduce and validate optimization strategies to get the best out of Anthropic.

You can also see your Anthropic costs in Datadog [Cloud Cost Management][6], allowing you to answer key questions: Which models or workspaces are generating the most cost? Which users or teams are driving the most spend? Are workloads using the right service tier (Standard, Batch, or Priority)? Are teams effectively using caching or ephemeral sessions? What's the cost breakdown between Claude Opus and Claude Sonnet?

**Minimum Agent version:** 7.69.0

## Setup

To get started with the Anthropic integration in Datadog, follow the steps below:

### 1. Identify your Anthropic plan and the key type you'll use

Your Anthropic organization is on either a **Platform** plan or an **Enterprise** plan, and the plan determines which API key type you use to authenticate this integration:

| Anthropic plan | API key type | Data ingested |
| --- | --- | --- |
| **Platform** | **Admin API key** | Organization-wide usage and cost, broken down by model, workspace, API key, and service tier. |
| **Enterprise** | **Analytics API key** | Per-user usage and cost, broken down by user, product (API, Claude Code, Claude.ai), model, context window, inference geography, and speed. Usage metrics are emitted in **1-hour buckets** after the hour closes on Anthropic's side, with a typical end-to-end latency of **1-3 hours**. Per-user cost data covers usage from **January 1, 2026** onward. |

Each Anthropic organization issues only one of these key types based on its plan, so most customers will configure exactly one key. If your company operates more than one Anthropic organization (for example, a Platform org and an Enterprise org), configure each one as a separate Datadog account.

All metrics and Cloud Cost Management line items emitted from an Enterprise (Analytics) account carry the `org_type:enterprise` tag. Platform (Admin) data is emitted without an `org_type` tag, so you can separate the two data sources in dashboards, monitors, and Cloud Cost Management filters using the presence (or absence) of `org_type:enterprise`.

### 2. Generate your Anthropic API key

Follow the path that matches your Anthropic plan:

- **Platform plan**: Generate an [Admin API key][5] from your Anthropic organization's settings, or ask your Anthropic account admin to create one for you.
- **Enterprise plan**: Generate an Analytics API key (with the `read:analytics` scope) at [claude.ai/analytics/api-keys][7]. Analytics API keys must be provisioned by your organization's **Primary Owner**.

Copy the API key to a secure location after you generate it.

### 3. Configure the Datadog integration

1. In Datadog, go to [**Integrations > Anthropic Usage and Costs**](https://app.datadoghq.com/integrations?integrationId=anthropic-usage-and-costs).
2. In the configuration panel, paste your **Admin API Key** or **Analytics API Key** into the API key field. Datadog automatically detects the key type and ingests the appropriate usage and cost data.
3. (Optional) Enable **Cost data ingestion** to send cost data to [Cloud Cost Management][6]. This requires Cloud Cost Management to be enabled on your Datadog account.
4. Click **Save Configuration**.

After you save the configuration, Datadog begins polling the appropriate Anthropic usage and cost endpoints and populates metrics in your environment. Usage metrics typically appear within 10 minutes, and cost data appears in Cloud Cost Management within 24 hours.

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
[7]: https://claude.ai/analytics/api-keys
