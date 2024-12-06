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

### Configuration

Vanta integration requires a Vanta account and its Client Id, and Client Secret. Below are the steps to fetch these details from Vanta console:

#### Get Vanta Credentials

1. Login to [Vanta Account][5] 
2. Go to the **Settings** and navigate to **Developer Console**.
3. Click on the **+Create** button at the upper right corner.
4. Specify the following details for the new application and click on **Create**.
    * **Name**: Enter a descriptive name for your application.
    * **Description**: Provide a brief overview of your application.
    * **App Type**: Select **Manage Vanta** 
5. Navigate to the **Application Info** section for the Client ID.
6. Click on **Generate client secret** for the Client secret.


#### Add Vanta Credentials

- Vanta App Client ID
- Vanta App Client Secret

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
