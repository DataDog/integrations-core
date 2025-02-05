# Metabase

## Overview

[Metabase][1] is a business intelligence analytics platform that can be used to ask questions about your data, or can be embedded in your apps to let your customers explore their data on their own.

Integrate Metabase with Datadog to gain insights into activity event logs, view logs, and query logs through the Metabase API. The data is normalized and enriched before ingestion. Pre-built dashboard visualizations provide immediate insights into Metabase logs.

## Setup

### Generate API credentials in Metabase

1. Log into your Metabase cloud instance as an administrator.
2. Click on the gear icon in the upper right corner.
3. Select **Admin settings**.
4. Go to the **Settings** tab.
5. Click on the **Authentication** tab from the left menu.
6. Scroll to the **API Keys** section and click **Manage**.
7. Click **Create API Key**.
8. Enter a key name.
9. Select the **Administrators** Group.
10. Click **Create** to get the generated API key.

### Get DNS alias of Metabase

1. Log into your Metabase cloud instance as an administrator.
2. Click on the gear icon in the upper right corner.
3. Select **Admin settings**.
4. Go to the **Settings** tab.
5. Click on the **Cloud** tab from the left menu.
6. Click on **Go to the Metabase Store**.
7. Log into your **Metabase Store** using Metabase credentials.
8. Go to the **Instances** tab.
9. Click on **DNS alias** section to get the DNS alias value.

### Connect your Metabase account to Datadog

1. Add your Metabase DNS alias and Metabase API key    
    |Parameters|Description|
    |--------------------|--------------------|
    |Metabase DNS alias|The DNS alias of your Metabase cloud instance. Should be minimum 3 characters long (small case letters, dashes and numbers only)|
    |Metabase API key|The API key used to authenticate the API requests.|

2. Click the Save button to save your settings.


## Data Collected

### Logs

The Metabase integration collects and forwards Metabase activity event logs, view logs, and query logs to Datadog.

### Metrics

The Metabase integration does not include any metrics.

### Events

The Metabase integration does not include any events.

## Support

For further assistance, contact [Datadog Support][2].

[1]: https://www.metabase.com/cloud/
[2]: https://docs.datadoghq.com/help/
