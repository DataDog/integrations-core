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
[metrics endpoint][4] and the use of a [Personal Access Token][7] to access the Supabase [Management API][6] for reading logs
if you choose to do so. 

If your Postgres log volume is continually greater than 200 messages/sec, Datadog recommends that you enable the 
[Datadog Log Drain][3] in your Supabase project and not select log collection via this integration.
If you choose to collect logs via this integration and currently have a Datadog Log Drain set up for your Supabase project, please disable it before proceeding. 
The logs collected from the Management API will be duplicate to those of the Log Drain.

### Retrieve the service_role API key

1. Log in to [Supabase][2] as an administrator.
2. Navigate to **Project Settings** > **API Keys**.
3. On the **Legacy API Keys** tab, retrieve the service_role API key.

### Generate a Personal Access Token
A Personal Access Token, PAT, is required to access the Supabase Management API and collect logs. The PAT inherits
the same permissions as the user who creates it. Since this integration only reads from the API, you have the option
to generate the PAT from a user in your organization with read-only permissions.

1. Log in to [Supabase][2] as an administrator.
2. (Optional) Create a user with read-only permissions and log in as that user.
   1. From the dashboard, navigate to **Team**
   2. Click **Invite member**
   3. In the **Member-role** dropdown, select **Read-only**.
   4. Complete the invitation and log in as the new user.
2. Navigate to the [Access Tokens page][7] of the dashboard.
3. Click on **Generate new token**.
4. Enter a name for the token, select the **Expires in** value _Never_ and click **Generate token**.
5. Note the token value at the top of the Access Tokens page and copy it for later use as it will not be displayed again.

### Connect your Supabase Cloud project to Datadog

1. Add your Supabase hosted project ID and service_role API key    
    |Parameters|Description|
    |--------------------|--------------------|
    |Project ID|Supabase project ID: E.g. `https://supabase.com/dashboard/project/<project_id>/settings/general`.|
    |Service_role API Key|API key needed for communication with the Metrics endpoint.|
    |Collect Logs|Enable this option to collect logs from your Supabase project instead of using a [Datadog Log Drain][3].|
    |Personal Access Token|Token needed for communication with the Management API.|

2. Click the **Save** button to save your settings.

## Data Collected

### Metrics

See [metadata.csv][5] for the full list of metrics provided by this integration.

If your project contains a Postgres read replica **and** you provide a Personal Access Token to the integration,
the integration will also collect metrics from the read replica, tagging the metrics with the appropriate
`supabase_identifier` value.

### Logs

When you enable this integration for your Supabase hosted project and choose to collect logs, all Postgres and application log
messages will be collected using the [Management API][6]. Alternatively, a [Datadog Log Drain][3] in Supabase can be used to 
deliver logs to Datadog. Regardless of how the log messages are delivered, this integration leverages Datadog's built-in log pipelines 
to parse and enrich the logs, facilitating easy search and detailed insights.

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
