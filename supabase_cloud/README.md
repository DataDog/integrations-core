## Overview

[Supabase][2] is a Postgres development platform that provides a managed Postgres database with additional features including
user authentication, client libraries, Edge Functions, Realtime subscriptions, Object Storage, and Vector embeddings.
While Supabase supports a self-hosted version, this integration only supports Supabase Cloud project instances.

With this integration, you can, per Supabase project:
- Collect essential Postgres Database metrics and monitor critical behavior on primary and replica instances.
- Collect Postgres server OS metrics and monitor CPU/Filesystem/Memory/Network load.
- Collect Postgres database logs which can include slow statements, errors, and audit statements.
- Collect Supabase application layer logs from edge functions and Auth/REST/Storage/Realtime APIs.
- Collect business logic log messages from your edge function applications.

## Setup

The Supabase Cloud integration requires the `service_role` API key to retrieve metrics from the hosted project's
[metrics endpoint][4]. If you want to collect logs, you also need a [Personal Access Token][7] to access the Supabase [Management API][6]. 

If your Postgres log volume exceeds 200 messages/sec, Datadog recommends using the
[Datadog Log Drain][3] instead of this integration's log collection feature.

**Important**: If you have a Datadog Log Drain configured for your Supabase project, disable it before enabling log collection via this integration to avoid duplicate logs.

### Retrieve the service_role API key

1. Log in to [Supabase][2] as an administrator.
2. Navigate to **Project Settings** > **API Keys**.
3. On the **Legacy API Keys** tab, retrieve the service_role API key.

### Generate a Personal Access Token
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

### Connect your Supabase Cloud project to Datadog

1. Add your Supabase hosted project ID and `service_role` API key
    |Parameter|Description|
    |--------------------|--------------------|
    |Project ID|Supabase project ID. For example: `https://supabase.com/dashboard/project/<project_id>/settings/general`.|
    |`service_role` API key|API key needed for communication with the Metrics endpoint.|
    |Collect Logs|Enable this option to collect logs from your Supabase project instead of using a [Datadog Log Drain][3].|
    |Personal Access Token|Token needed for communication with the Management API. Required only if **Collect Logs** is enabled.|

2. Click the **Save** button to save your settings.

## Data Collected

### Metrics

See [metadata.csv][5] for the full list of metrics provided by this integration.

If your project contains a Postgres read replica **and** you provide a Personal Access Token,
the integration also collects metrics from the read replica and tags them with the appropriate
`supabase_identifier` value.

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
