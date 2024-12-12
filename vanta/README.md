# Vanta

## Overview

[Vanta][1] is a compliance automation tool that assists businesses in obtaining security certifications and identifying vulnerabilities. It streamlines compliance processes through automation, making monitoring and documentation easier to establish solid security practices.

The Vanta integration collects below types of data:

1. Logs:
    * **Vulnerabilities**: This endpoint contains information about all vulnerabilities that have not been remediated and have exceeded their SLA deadlines.
2. Metrics:
    * **Frameworks**: This endpoint contains information about different framework analytics such as completed controls, passing documents, and successful tests.

This integration collects logs and metrics from the sources listed above and sends them to Datadog for analysis with our Log and Metrics Explorer and Cloud SIEM products.

* [Log Explorer][2]
* [Metrics Explorer][3]
* [Cloud SIEM][4]

## Setup

### Generate API credentials in Vanta

1. Log in to [Vanta Account][5]
2. Go to the **Settings** and navigate to **Developer Console**.
3. Click the **+Create** button at the upper right corner.
4. Specify the following details for the new application and click **Create**.
    * **Name**: Enter a descriptive name for your application.
    * **Description**: Provide a brief overview of your application.
    * **App Type**: Select **Manage Vanta** 
5. Navigate to the **Application Info** section for the Client ID.
6. Click **Generate client secret** for the Client Secret.


### Connect your Vanta Account to Datadog

1. Add your Client ID and Client Secret
    |Parameters|Description|
    |--------------------|--------------------|
    |Client ID|The Client ID of application on Vanta.|
    |Client Secret|The Client Secret of application on Vanta.|
2. Click the Save button to save your settings.

## Data Collected

### Logs 

The Vanta integration collects and forwards Vulnerabilities logs to Datadog.

### Metrics

The Vanta integration collects and forwards Frameworks metrics to Datadog.

{{< get-metrics-from-git "vanta" >}}

### Service Checks

The Vanta integration does not include any service checks.

### Events

The Vanta integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][6].

[1]: https://www.vanta.com/
[2]: https://docs.datadoghq.com/logs/explorer/
[3]: https://docs.datadoghq.com/metrics/explorer/
[4]: https://www.datadoghq.com/product/cloud-siem/
[5]: https://app.vanta.com/login/
[6]: https://docs.datadoghq.com/help/
