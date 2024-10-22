# StreamNative

## Overview

[StreamNative][1] provides an enterprise-grade messaging and event streaming platform built on Apache Pulsar. It offers scalable, real-time data streaming solutions with features like multi-tenancy, geo-replication, and seamless integration with cloud services.

The StreamNative integration collects below types of metrics:

1. Health
2. Pulsar Resource
3. Source Connector
4. Sink Connector
5. Kafka Connect

## Setup

### Configuration

StreamNative integration requires a StreamNative account and its Client Id, Client Secret, Organization ID and Instance Name. Below are the steps to fetch these details from StreamNative console:

#### Steps to retrieve Organization ID, Instance Name, Client Id & Client Secret

1. Login to the [StreamNative Cloud Console Account][2] 
2. Go to the profile icon and select to the **Organizations** option.
3. Go into the **Organization** from which data needs to be collected in the Datadog.
4. Copy and save the **Organization ID** to configure in the Integration.
5. From the **Select an Instance** section, Copy and save the **Instance Name** to configure in the Integration.
6. Go to the profile icon and select the **Accounts & Accesses** tab.
7. Choose the Service Account for which **Admin** permission is **True**.
8. If the Service Account does not exist, click on **New -> Service Account** to create a new one, and ensure the **Super Admin** type is enabled.
9. Click on the 3 dots on the right side of the selected Service Account.
10. Click on **Download OAuth2 Key**, this file will have required **Client ID** & **Client Secret** to configure in the Integration.


#### StreamNative DataDog integration configuration

Configure the Datadog endpoint to forward StreamNative metrics to Datadog.

1. Navigate to the `StreamNative` integration tile in Datadog.
2. Add your StreamNative credentials.

| StreamNative parameters | Description                                    |
| ------------------------------ | ---------------------------------------------  |
| Organization ID                   | Organization ID of your StreamNative account.     |
| Instance Name                   | Instance name of the desired organization.     |
| Client ID                   | Client ID of your service account.     |
| Client Secret                   | Client Secret of your service account.     |



## Data Collected

### Logs 

The StreamNative integration does not include any logs.

### Metrics

The StreamNative integration collects and forward below metrics to Datadog.

1. Health
2. Pulsar Resource
3. Source Connector
4. Sink Connector
5. Kafka Connect

### Service Checks

The StreamNative integration does not include any service checks.

### Events

The StreamNative integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: https://streamnative.io/
[2]: https://console.streamnative.cloud/
[3]: https://docs.datadoghq.com/help/
