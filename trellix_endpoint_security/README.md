## Overview

[Trellix Endpoint Security (ENS)][1] protects servers, computer systems, laptops, and tablets against known and unknown threats. These threats include malware, suspicious communications, unsafe websites, and downloaded files. Trellix Endpoint Security enables multiple defense technologies to communicate in real time to analyze and protect against threats.

This integration ingests the following logs:

- **Threat Events**: This endpoint provides details about threat events triggered by Trellix Endpoint Security, including threat prevention, web control, firewall, and adaptive threat protection.

This integration provides enrichment and visualization for above mentioned event types. It helps to visualize detailed insights into security trends, threats, and policy violations through the out-of-the-box dashboards. Also, This integration provides out of the box detection rules.

## Setup

### Configuration

#### Get Credentials of Trellix Endpoint Security

1. Log in to the Trellix ePO Saas.
2. Navigate to the **Trellix Developer Portal** using [this][2] link.
3. Under **Self-Service**, select **API Access Management**.
4. In the **Credential Configurations** section, provide the following details:
   - **Client Type**: Enter a descriptive and identifiable name.
   - **APIs**: Choose **Events** from the dropdown.
   - **Method Types**: Select **GET**.
5. Click **Request** to submit the request. It typically takes 2-3 days to process. You will be notified once your credentials are ready.
6. When your credentials are available, generate your Client credentials by clicking **Generate** under **Create Client Credentials**.
7. Copy and securely store the API key from **Access Management**, along with the Client ID and Client Secret from **Create Client Credentials**.

#### Configure the Trellix Endpoint Security and Datadog Integration

Configure the Datadog endpoint to forward Trellix Endpoint Security logs to Datadog.

1. Navigate to `Trellix Endpoint Security`.
2. Add your Trellix Endpoint Security credentials.

| Trellix Endpoint Security Parameters | Description                            |
| ------------------------------------ | -------------------------------------- |
| Client ID                            | The Client ID of Trellix ePO SaaS.     |
| Client Secret                        | The Client Secret of Trellix ePO SaaS. |
| API Key                              | The API Key of of Trellix ePO SaaS.    |

## Data Collected

### Logs

The Trellix Endpoint Security integration collects and forwards events related to threat prevention, web control, firewall, and adaptive threat protection to Datadog.

### Metrics

The Trellix Endpoint Security integration does not include any metrics.

### Events

The Trellix Endpoint Security integration does not include any events.

## Support

For additional assistance, contact [Datadog support][3].

[1]: https://www.trellix.com/products/endpoint-security/
[2]: https://developer.manage.trellix.com/mvision/selfservice/home
[3]: https://docs.datadoghq.com/help/
