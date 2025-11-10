## Overview

[Supabase][2] is a Postgres development platform that provides a Postgres database with additional features including 
Authentication, instant APIs, Edge Functions, Realtime subscriptions, Object Storage, and Vector embeddings. 
While Supabase supports a self-hosted version, this integration only supports Supabase Cloud project instances.

With this integration, you can, per Supabase project:
- Collect essential Postgres Database metrics and monitor critical behavior.
- Collect Postgres server OS metrics and monitor CPU/Filesystem/Memory/Network load.
- With a [Supabase Log Drain][3] enabled:
  - Collect Postgres database logs which can include slow statements, errors, and audit logs.
  - Collect Supabase application layer logs such as edge functions and Auth/REST/Storage/Realtime APIs.
  - Collect business logic log messages from your edge function applications.

## Setup

The Supabase Cloud integration requires the service_role API key to retrieve metrics from the hosted project's
[metrics endpoint][4] only.

### Retrieve the service_role API key

1. Log in to [Supabase][2] as an administrator.
2. Navigate to **Project Settings** > **API Keys**.
3. On the **Legacy API Keys** tab, retrieve the service_role API key.

### Connect your Supabase Cloud project to Datadog

1. Add your Supabase hosted project ID and service_role API key    
    |Parameters|Description|
    |--------------------|--------------------|
    |Project ID|Supabase project ID: E.g. `https://supabase.com/dashboard/project/<project_id>/settings/general`.|
    |Service_role API Key|API key needed for communication with the Metrics endpoint.|

2. Click the **Save** button to save your settings.

## Data Collected

### Metrics

See [metadata.csv][5] for the full list of metrics provided by this integration.

### Logs

When you enable a Log Drain within Supabase for your hosted project, all Postgres and application log
messages will be pushed to Datadog. Datadog leverages its built-in log pipelines to parse and enrich these logs, 
facilitating easy search and detailed insights.

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

