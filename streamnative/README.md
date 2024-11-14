# StreamNative

## Overview

[StreamNative][1] provides an enterprise-grade messaging and event streaming platform built on Apache Pulsar. It offers scalable, real-time data streaming solutions with features like multi-tenancy, geo-replication, and seamless integration with cloud services.

The StreamNative integration collects the below types of [metrics][2]:

1. Health
2. Pulsar Resource
3. Source Connector
4. Sink Connector
5. Kafka Connect

## Setup

### Configuration

#### Get StreamNative credentials

##### Log in to the [StreamNative Cloud Console Account][3].
##### Get the `Organization ID` and `Instance Name`:
1. Click the profile icon and select the **Organizations** option.
2. Select the **Organization** for which data needs to be collected.
3. Obtain the **Instance Name** from the **Select an Instance** dropdown.
##### Get the `Client ID` and `Client Secret`:
1. Click the profile icon and select the **Accounts & Accesses** tab.
2. Select the Service Account for which **Admin** permission is **Enabled**.
3. If the Service Account does not exist, click on **New -> Service Account** to create a new one, and ensure the **Super Admin** option is enabled.
4. Click on the `...` button on the right side of the selected Service Account.
5. Click **Download OAuth2 Key** to get the **Client ID** and **Client Secret**.


#### Add StreamNative credentials

- Organization ID 
- Instance Name
- Client ID  
- Client Secret  


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