## Overview

[Metabase][1] is a business intelligence analytics platform that can be used to ask questions about your data, or can be embedded in your apps to let your customers explore their data on their own.

Integrate Metabase with Datadog to gain insights into activity event logs through the Metabase API. The data is normalized and enriched before ingestion. Pre-built dashboard visualizations provide immediate insights into Metabase activity events.

## Setup

### Configuration

#### Get config parameters of Metabase

##### DNS alias

1. Log in to your Metabase cloud instance as an administrator.
2. Click on the gear icon in the upper right corner.
3. Select **Admin settings**.
4. Go to the **Settings** tab.
5. Click on the **Cloud** tab from the left menu.
6. Click on **Go to the Metabase Store**.
7. Log in to your **Metabase Store** using Metabase credentials.
8. Go to the **Instances** tab.
9. Click on **DNS alias**.
10. Copy the text box value.

##### API Key

1. Log in to your Metabase cloud instance as an administrator.
2. Click on the gear icon in the upper right corner.
3. Select **Admin settings**.
4. Go to the **Settings** tab.
5. Click on the **Authentication** tab from the left menu.
6. Scroll to the **API Keys** section and click **Manage**.
7. Click **Create API Key**.
8. Enter a key name.
9. Select the **Administrators** Group.
10. Click **Create**.
11. Copy the generated API key.

#### Configure the Metabase and Datadog integration

Configure the Metabase endpoint to forward Metabase activity logs to Datadog.

1. Navigate to `Metabase` integration on Datadog platform.
2. Add your Metabase credentials.

| Metabase Parameters | Description                                                          |
|---------------------|----------------------------------------------------------------------|
| DNS alias           | The DNS alias of your Metabase cloud instance.                       |
| API key             | The API key used to authenticate the API requests.                   |

## Data Collected

### Logs

The Metabase integration collects and forwards Metabase activity event logs to Datadog.

### Metrics

The Metabase integration does not include any metrics.

### Events

The Metabase integration does not include any events.

## Support

For further assistance, contact [Datadog Support][2].

[1]: https://www.metabase.com/cloud/
[2]: https://docs.datadoghq.com/help/

