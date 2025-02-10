# StreamNative

## Overview

[StreamNative][1] provides an enterprise-grade messaging and event streaming platform built on Apache Pulsar. It offers scalable, real-time data streaming solutions with features like multi-tenancy, geo-replication, and seamless integration with cloud services.

The StreamNative integration collects the following types of [metrics][2]:

1. Health
2. Pulsar Resource
3. Source Connector
4. Sink Connector
5. Kafka Connect

## Setup

### Generate API credentials in StreamNative

1. Log into [StreamNative Cloud Console Account][3].
2. Click the profile icon and navigate to the **Accounts & Accesses** tab.
3. Find the Service Account with **Admin** permissions set to **Enabled**.
   - If no Service Account exists, select **New -> Service Account** to create one, and make sure to enable the **Super Admin** option.
4. On the right side of the chosen Service Account, click the `...` button.
5. Select **Download OAuth2 Key** to obtain the **Client ID** and **Client Secret**.

### Get `Organization ID` and `Instance Name`

1. Click the profile icon and select **Organizations**.
2. Choose the **Organization** for which data needs to be collected.
3. From the **Select an Instance** dropdown, get the **Instance Name**.


### Connect your StreamNative account to Datadog

1. Add your organization ID, instance name, client ID, and client secret.
    |Parameters|Description|
    |--------------------|--------------------|
    |Organization ID|Organization ID of your StreamNative account.|
    |Instance Name|Instance name of the corresponding organization.|
    |Client ID |Client ID of your service account.|
    |Client Secret|Client secret of your service account.|
2. Click the **Save** button to save your settings.


## Data Collected

### Logs 

The StreamNative integration does not include any logs.

### Metrics

The StreamNative integration collects and forwards the following metrics to Datadog.

{{< get-metrics-from-git "streamnative" >}}

### Service Checks

The StreamNative integration does not include any service checks.

### Events

The StreamNative integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][4].

[1]: https://streamnative.io/
[2]: https://docs.streamnative.io/docs/cloud-metrics-api#metrics-endpoint
[3]: https://console.streamnative.cloud/
[4]: https://docs.datadoghq.com/help/
