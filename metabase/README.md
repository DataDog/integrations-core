# Metabase

## Overview

[Metabase][1] is a business intelligence analytics platform that can be used to ask questions about your data, or can be embedded in your apps to let your customers explore their data on their own.

Integrate Metabase with Datadog for:

**Log Collection**: Gain insights into activity event logs, view logs, and query logs through the Metabase API. The data is normalized and enriched before ingestion. Pre-built dashboard visualizations provide immediate insights into Metabase logs.

**Data Lineage**: View end-to-end lineage across Metabase collections, dashboards, and cards to understand dependencies and downstream impact.

**Note**: Lineage is derived from your data warehouse, so the Metabase integration produces lineage only when at least one [supported data warehouse destination][3] is also connected to Datadog. Log collection has no such requirement.

## Setup

### Prerequisites

- This integration requires a Metabase Pro or Enterprise plan.

### Generate API credentials in Metabase

1. Log into your Metabase instance as an administrator.
2. Click on the gear icon in the upper right corner.
3. Select **Admin settings**.
4. Go to the **Settings** tab.
5. Click on the **Authentication** tab from the left menu.
6. Select the **API Keys** section.
7. Click **Create API Key**.
8. Enter a key name.
9. Select the **Administrators** Group.
10. Click **Create** to get the generated API key.

### Get DNS alias of Metabase (required for cloud instances only)

1. Log into your Metabase cloud instance as an administrator.
2. Click on the gear icon in the upper right corner.
3. Select **Admin settings**.
4. Go to the **Settings** tab.
5. Click on the **Cloud** tab from the left menu.
6. Click on **Go to the Metabase Store**.
7. Log into your **Metabase Store** using Metabase credentials.
8. Go to the **Instances** tab.
9. Click on **DNS alias** section to get the DNS alias value.

### Get self-hosted instance domain of Metabase (required for self-hosted instances only)

**Note**: Your self-hosted Metabase instance must be accessible from the internet via HTTPS only, and ensure that the API is not being intercepted by SAML/SSO at the proxy/network level.
1. Log in to your Metabase instance as an administrator.
2. Click on the gear icon in the upper right corner.
3. Select **Admin settings**.
4. Go to the **Settings** tab.
5. Click on the **General** tab from the left menu.
6. Under **SITE URL**, copy the domain portion of the URL. For example, if the URL is `https://example.com`, copy `example.com`.

### Connect your Metabase account to Datadog

1. Navigate to the [Metabase integration tile][5] and enter the following information:

    |Parameter|Description|
    |--------------------|--------------------|
    |Account name|Used to identify this account in Datadog.|
    |Instance type|The hosting type of your Metabase instance. Valid values are `cloud` or `self-hosted`. Default is `cloud`.|
    |DNS alias|The DNS alias of your Metabase cloud instance (required for cloud instances only). Must be at least three characters long and contain only lowercase letters, dashes, and numbers.|
    |Self-hosted instance domain|The domain of your self-hosted Metabase instance (required for self-hosted instances only). Must be publicly accessible through HTTPS only (for example, `example.com`).|
    |API key|The API key used to authenticate the API requests.|

2. Click **Save**.

## What's next

When your Metabase account is successfully connected, Datadog syncs and automatically derives lineage from warehouse tables and columns to Metabase cards and dashboards.

Initial syncs may take up to several hours depending on the size of your Metabase deployment.

After syncing, you can explore your Metabase assets and their upstream dependencies in the [Data Observability Catalog][4].

## Data Collected

### Logs

The Metabase integration collects and forwards Metabase activity event logs, view logs, and query logs to Datadog.

### Metrics

The Metabase integration does not include any metrics.

### Events

The Metabase integration does not include any events.

## Support

For further assistance, contact [Datadog Support][2].

[1]: https://www.metabase.com/
[2]: https://docs.datadoghq.com/help/
[3]: https://docs.datadoghq.com/data_observability/quality_monitoring/data_warehouses/
[4]: /data-obs/catalog
[5]: /integrations/metabase
