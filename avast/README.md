# Avast

## Overview

[Avast Business Hub][1] is a cloud-based platform that helps businesses manage their Avast security solutions. It offers real-time threat monitoring, detailed reporting, and centralized security control for endpoints, ensuring comprehensive protection across the network and safeguarding against cyberthreats.

The Avast integration collects the following types of logs:

- **Threat**: This endpoint contains information about devices with detected threats, including the type of threat and detection time.
- **Task**: This endpoint contains a summary of tasks performed on devices, including execution details, progress, and completion status.
- **Patch**: This endpoint contains details about patches for devices, allowing monitoring of the health and security of device software and applications.
- **Audit**: This endpoint contains details about user activities, including changes to policies and user access.

This integration collects logs from the sources listed above and sends them to Datadog for analysis with our Log Explorer and Cloud SIEM products.

* [Log Explorer][2]
* [Cloud SIEM][3]

## Setup

### Configuration

Avast integration requires an Avast Business Hub account and its Client ID, and Client Secret. Below are the steps to fetch these details from Avast Business Hub console:

#### Get Avast Credentials

1. Login to the [Avast Business Hub][4] Account.
2. Navigate and click the gear(settings) icon.
3. In the **Settings** section, click **Integrations**.
4. Click **Add a new integration**.
5. Provide an integration name.
6. Select Integration scope as **API Gateway**, then click **Generate a secret**.
7. Obtain the **Client ID** and the **Client Secret** for configuration.

#### Add Avast Credentials

1. Avast `Client ID`
2. Avast `Client Secret`

## Data Collected

### Logs 

The Avast integration collects and forwards security logs to Datadog.

### Metrics

The Avast integration does not include any metrics.

### Service Checks

The Avast integration does not include any service checks.

### Events

The Avast integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][5].

[1]: https://www.avast.com/business/business-hub/
[2]: https://docs.datadoghq.com/logs/explorer/
[3]: https://www.datadoghq.com/product/cloud-siem/
[4]: https://businesshub.avast.com/
[5]: https://docs.datadoghq.com/help/