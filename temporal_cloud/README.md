## Overview

[Temporal Cloud][1] is a scalable platform for orchestrating complex workflows, with built-in reliability, resilience and timing controls enabling developers to focus on application logic without worrying about fault tolerance and consistency.


This integration collects Temporal Cloud metrics and directs them into Datadog to provide insights into system health, workflow efficiency, task execution and performance bottlenecks.

## Setup

### Generate Metrics Endpoint URL in Temporal Cloud

1. In order to generate security CA Certificate and End-entity Certificate refer to this [link][2].
    - **Note**: It is recommended to define longer expiry duration of the certificates.
2. Log in to [Temporal Cloud][3] with an Account Owner or Global Admin role.
3. Go to **Settings** and select the **Observability** tab.
4. Under the **Certificates** section, add your root CA certificate (.pem file content) and save it.
    - **Note**: If an observability endpoint is already set up, you can append your root CA certificate.
5. Click **Save** to generate the endpoint URL under the **Endpoint** section. The URL will look like: https://<account_id>.tmprl.cloud/prometheus.


### Connect your Temporal Cloud account to Datadog

1. Add your Account ID, End-entity Certificate file content and End-entity Certificate key file content    
    |Parameters|Description|
    |--------------------|--------------------|
    |Account ID|Temporal Cloud account ID to be used as part of metrics endpoint URL: https://<account_id>.tmprl.cloud/prometheus.|
    |End-entity Certificate file content|Content of End-entity Certificate for secure access and communication with Metrics Endpoint.|
    |End-entity Certificate key file content|Content of End-entity Certificate key for secure access and communication with Metrics Endpoint.|

2. Click the Save button to save your settings.


## Data Collected

### Metrics

The Temporal Cloud integration collects and forwards Frontend Service metrics, Poll metrics, Replication lag metrics, Schedule metrics, Service latency metrics and Workflow metrics to Datadog. See [metadata.csv][4] for a list of metrics provided by this integration.


### Service Checks

The Temporal Cloud integration does not include any service checks.

### Events

The Temporal Cloud integration does not include any events.

## Support

Need help? Contact [Datadog support][5].

[1]: https://temporal.io/cloud/
[2]: https://docs.temporal.io/cloud/certificates#use-certstrap/
[3]: https://cloud.temporal.io/
[4]: https://github.com/DataDog/integrations-core/blob/master/temporal_cloud/metadata.csv
[5]: https://docs.datadoghq.com/help/
