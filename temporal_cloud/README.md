## Overview

[Temporal Cloud][1] is a scalable platform for orchestrating complex workflows, with built-in reliability, resilience, and timing controls. Temporal Cloud enables developers to focus on application logic without worrying about fault tolerance and consistency.


This integration gathers Temporal Cloud metrics into Datadog, offering insights into system health, workflow efficiency, task execution, and performance bottlenecks.

## Setup

### Generate a Metrics endpoint URL in Temporal Cloud

1. To generate a CA certificate and an end-entity certificate, see [certificate management][2].
    - **Note**: An expired root CA certificate invalidates all downstream certificates. To avoid disruptions to your systems, use certificates with long validity periods.
2. Log in to [Temporal Cloud][3] with an account owner or global admin role.
3. Go to **Settings**, and select the **Observability** tab.
4. Under the **Certificates** section, add your root CA certificate (`.pem` file content) and save it.
    - **Note**: If an observability endpoint is already set up, you can append your root CA certificate.
5. Click **Save** to generate the endpoint URL under the **Endpoint** section. The URL should look like: `https://<account_id>.tmprl.cloud/prometheus`.


### Connect your Temporal Cloud account to Datadog

1. Add your Account ID, End-entity Certificate file content, and End-entity Certificate key file content    
    |Parameters|Description|
    |--------------------|--------------------|
    |Account ID|Temporal Cloud account ID to be used as part of the metrics endpoint URL: `https://<account_id>.tmprl.cloud/prometheus`.|
    |End-entity certificate file content|Contents of the end-entity certificate for secure access and communication with the Metrics endpoint.|
    |End-entity certificate key file content|Content of the end-entity certificate key for secure access and communication with the Metrics endpoint.|

2. Click the **Save** button to save your settings.


## Data Collected

### Metrics

See [metadata.csv][4] for a list of metrics provided by this integration.


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
