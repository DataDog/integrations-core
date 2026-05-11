# Anthropic Compliance Logs

## Overview

Datadog's Anthropic Compliance Logs integration ingests audit activity events from Anthropic's [Compliance API][1]. With this integration, security and compliance teams can:

- **Monitor SSO sign-ins and authentication events** across your organization
- **Track API key lifecycle** (creation, deletion, scope updates) for Admin, Platform, and Scoped API keys
- **Audit Anthropic Console activity** including member invites, role changes, and workspace updates
- **Investigate Claude usage** at the audit level (chat views, project access, file operations)
- **Detect security-sensitive events** with the included Cloud SIEM detection rules

The Compliance API is available to Anthropic Enterprise plan customers with the Compliance API enabled in their organization settings.

## Setup

### Prerequisites

- An Anthropic **Enterprise plan** subscription
- **Compliance API enabled** in Anthropic Organization settings under **Data and privacy**
- An **Admin API key** (prefix `sk-ant-admin01-`) with the `read:compliance_activities` scope, or a dedicated **Compliance Access key** (prefix `sk-ant-api01-`)

### 1. Enable the Compliance API in Anthropic

1. Log in to the Anthropic Console as a Primary Owner.
2. Navigate to **Organization settings -> Data and privacy**.
3. Find the **Compliance API** section and click **Enable**.

### 2. Generate or locate an Admin API key

1. Navigate to **Organization settings -> API keys**.
2. Generate a new Admin API key, or use the existing key already configured for the [Anthropic Usage and Costs][2] integration (the same key is reused).
3. Copy the key to a secure location.

### 3. Configure the Datadog integration

1. In Datadog, go to [**Integrations -> Anthropic Compliance Logs**](https://app.datadoghq.com/integrations?integrationId=anthropic-compliance-logs).
2. In the configuration panel, paste your **Admin API Key**.
3. Toggle **Enable Compliance Logs** to ON.
4. Click **Save Configuration**.

### 4. Validate

1. Wait up to 5 minutes for the first crawl.
2. Open [Log Explorer][3] and filter on `source:anthropic service:anthropic.compliance`.
3. Confirm events appear with `evt.name` values such as `claude_chat_viewed`, `admin_api_key_created`, or `user_signed_in_sso`.

## Data Collected

### Logs

The integration collects audit activity events from `GET /v1/compliance/activities`. Each event includes:

- A timestamp (`created_at`) with microsecond precision
- An actor (user, API key, SCIM, or system) with email, user ID, IP address, and User-Agent when applicable
- An activity `type` such as `user_signed_in_sso`, `admin_api_key_created`, `org_user_invite_accepted`, or `claude_chat_viewed` (150+ activity types across 35+ categories)
- Organization and workspace context

Logs are tagged `source:anthropic service:anthropic.compliance` and processed by a Datadog log pipeline that flattens the actor object into standard `usr.*` and `network.client.*` attributes and enriches the source IP with GeoIP and the User-Agent string.

### Metrics

Anthropic Compliance Logs does not include any metrics.

### Service Checks

Anthropic Compliance Logs does not include any service checks.

### Events

Anthropic Compliance Logs does not include any events.

## Troubleshooting

- **No logs after 10 minutes**: Verify the Compliance API is enabled in Anthropic Organization settings under Data and privacy.
- **HTTP 403**: Confirm the Compliance API is enabled and that the Admin API key has the `read:compliance_activities` scope.
- **Enterprise gate**: The Compliance API is only available on the Enterprise plan.

Need help? Contact [Datadog support][4].

[1]: https://docs.anthropic.com/en/api/administration-api
[2]: https://app.datadoghq.com/integrations?integrationId=anthropic-usage-and-costs
[3]: https://app.datadoghq.com/logs?query=source%3Aanthropic+service%3Aanthropic.compliance
[4]: https://docs.datadoghq.com/help/
