# Avast

## Overview

[Avast Business Hub][1] is a cloud-based platform that helps businesses manage their Avast security solutions. It offers real-time threat monitoring, detailed reporting, and centralized security control for endpoints, ensuring protection across the network and safeguarding against cyberthreats.

The Avast integration collects the following types of logs:

- **Threat**: This endpoint contains information about devices with detected threats, including the type of threat and detection time.
- **Task**: This endpoint contains a summary of tasks performed on devices, including execution details, progress, and completion status.
- **Patch**: This endpoint contains details about patches for devices, allowing monitoring of the health and security of device software and applications.
- **Audit**: This endpoint contains details about user activities, including changes to policies and user access.

This integration collects logs from the sources listed above and sends them to Datadog for analysis by [Log Explorer][2] and [Cloud SIEM][3].

## Setup

### Generate API credentials in Avast

1. Log in to your [Avast Business Hub][4] account.
2. Click the gear(**settings**) icon.
3. In the **Settings** section, click **Integrations**.
4. Click **Add a new integration**.
5. Provide an integration name.
6. Select **Integration scope** as **API Gateway**.
7. Click **Generate a secret**.
8. The **Client ID** and **Client Secret** appear.

### Connect your Avast account to Datadog

1. Add your Client ID and Client secret
    |Parameters|Description|
    |--------------------|--------------------|
    |Client ID|The Avast Business Hub integration client ID.|
    |Client secret|The Avast Business Hub integration client secret.|
2. Click the **Save** button to save your settings.

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
