## Overview

[Supabase][2] is a Postgres development platform that provides a managed Postgres database with additional features including
user authentication, client libraries, Edge Functions, Realtime subscriptions, Object Storage, and Vector embeddings.
While Supabase supports a self-hosted version, this integration only supports Supabase Cloud project instances.

With this integration, you can, per Supabase project:
- Collect essential Postgres Database metrics and monitor critical behavior on primary and replica instances.
- Collect Postgres server OS metrics and monitor CPU, filesystem, memory, and network load.
- Collect Postgres database logs which can include slow statements, errors, and audit statements.
- Collect Supabase application layer logs from edge functions and Auth, REST, Storage, and Realtime APIs.
- Collect business logic log messages from your edge function applications.

## Setup

Connect your Supabase Cloud project to Datadog using OAuth. OAuth is the only way to connect a new project;
Personal Access Token (PAT) setup is **deprecated** and no longer available for new accounts. Existing PAT-based
accounts continue to collect data, but can no longer be edited from the Datadog integration tile. Re-authenticate
with OAuth as described below to make changes.

If your Postgres log volume exceeds 200 messages per second, Datadog recommends using the
[Datadog Log Drain][3] instead of this integration's log collection feature.

**Important**: If you have a Datadog Log Drain configured for your Supabase project, disable it before enabling log collection via this integration to avoid duplicate logs.

### Connect your Supabase Cloud project to Datadog (OAuth)

1. In the Datadog app, navigate to the [Supabase Cloud integration tile][8] and click **Add account**.
2. Fill in the account settings:
    |Parameter|Description|
    |--------------------|--------------------|
    |Account name|Used to identify this account in Datadog.|
    |Project ID|Supabase project ID, found in the URL of your Supabase project. For example: `https://app.supabase.com/project/<project_id>`.|
    |Collect Logs|Enable this option to collect logs from your Supabase project instead of using a [Datadog Log Drain][3]. Uses the Management API, limited by its rate limits; if you generate more than ~200 log events per second, use Supabase's log drain feature instead.|
    |Enable Database Monitoring|Enable this option to get query performance insights for your Supabase databases.|

3. Click **Connect via OAuth**. You're redirected to Supabase to log in (if you aren't already) and select the
   organization that owns the project entered above.
4. Review the permissions Datadog is requesting and click **Authorize**.
5. You're redirected back to the Supabase Cloud integration tile in Datadog, where the newly connected account now appears.

### [Deprecated] Personal Access Token setup

The following steps only apply to accounts that were connected before OAuth support was added, and are kept here
for reference. To connect a new project, use the [OAuth setup](#connect-your-supabase-cloud-project-to-datadog-oauth)
above instead.

#### Retrieve the service_role API key

1. Log in to [Supabase][2] as an administrator.
2. Navigate to **Project Settings** > **API Keys**.
3. On the **Legacy API Keys** tab, retrieve the `service_role` API key.

#### Generate a Personal Access Token
A Personal Access Token (PAT) is required to access the Supabase Management API and collect logs.

1. Log in to [Supabase][2] as an administrator or a user with appropriate permissions.

   **Note**: The Personal Access Token inherits the same permissions as the user who creates it. Since this integration only reads from the API, you can optionally create a user with read-only permissions:
   1. From the dashboard, navigate to **Team**.
   2. Click **Invite member**.
   3. In the **Member-role** dropdown, select **Read-only**.
   4. Complete the invitation and log in as the new user.

2. Navigate to the [Access Tokens page][7] of the dashboard.
3. Click **Generate new token**.
4. Enter a name for the token, select **Never** for **Expires in**, and click **Generate token**.
5. Copy the token value displayed at the top of the page. Store it securely, as it won't be displayed again.

## Data Collected

### Metrics

See [metadata.csv][5] for the full list of metrics provided by this integration.

If your project contains a Postgres read replica **and** the account was connected using a deprecated
Personal Access Token, the integration also collects metrics from the read replica and tags them with the
appropriate `supabase_identifier` value.

### Logs

When you enable log collection for this integration, all Postgres and application log messages are collected using the [Management API][6]. Alternatively, you can use a [Datadog Log Drain][3] in Supabase to deliver logs to Datadog. Regardless of the delivery method, this integration uses Datadog's built-in log pipelines to parse and enrich the logs for easier searching and more detailed insights.

### Events

The Supabase Cloud integration does not include any events.

### Service Checks

The Supabase Cloud integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: https://supabase.com/
[3]: https://supabase.com/docs/guides/telemetry/log-drains
[4]: https://supabase.com/docs/guides/telemetry/metrics
[5]: https://github.com/DataDog/integrations-core/blob/master/supabase_cloud/metadata.csv
[6]: https://supabase.com/docs/reference/api/introduction
[7]: https://supabase.com/dashboard/account/tokens
[8]: https://app.datadoghq.com/integrations/supabase-cloud
