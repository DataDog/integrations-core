# Palo Alto Cortex XDR

## Overview

[Palo Alto Cortex XDR][1] is a comprehensive detection and response platform that provides advanced threat protection across endpoints, networks, and cloud environments. It integrates endpoint protection, network security, and analytics to offer real-time visibility and response capabilities and combat sophisticated cyber threats effectively.

This integration ingests the following logs:

- Incident: Represents information of artifacts, assets, and alerts from a threat event, including their severity, status, and the users who handle them.
- Alert: Represents real-time analysis of alerts, including their severity, frequency, and source.

The Palo Alto Cortex XDR integration seamlessly collects the data of Palo Alto Cortex XDR logs using REST APIs. Before ingesting the data, it normalizes and enriches the logs, ensuring a consistent data format and enhancing information content for downstream processing and analysis. The integration provides insights into incidents and alerts using out-of-the-box dashboards.

## Setup

### Generate API credentials in Palo Alto Cortex XDR

1. Log into your **Palo Alto Cortex XDR account**.
2. Navigate to **Settings** > **Configurations** > **Integrations** > **API Keys**.
3. Click on **New Key**.
4. Choose the type of API key based on your desired security level, **Advanced** or **Standard**.
5. If you want to define a time limit on the API key authentication, check **Enable Expiration Date**, and then select the **expiration date and time**. Navigate to **Settings** > **Configurations** > **Integrations** > **API Keys** to track the **Expiration Time** setting for each API key.
6. Provide a comment that describes the purpose for the API key, if desired.
7. Select the desired level of access for this key from existing **Roles**, or you can select **Custom** to set the permissions granularly.
8. Click **Generate** to generate the API key.

### Get API key ID of Palo Alto Cortex XDR

1. In the API Keys table, locate the ID field.
2. Note your corresponding ID number. This value represents the **x-xdr-auth-id:{key_id}** token.

### Get FQDN of Palo Alto Cortex XDR

1. Right-click your API key and select **View Examples**.
2. Copy the **CURL Example** URL. The example contains your unique **FQDN**.

### Connect your Palo Alto Cortex XDR account to Datadog

1. Add your Palo Alto Cortex XDR credentials.

    | Parameters   | Description  |
    | -------------| ------------ |
    | API key      | The API key from Palo Alto Cortex XDR. |
    | API Key ID   | The auth ID from Palo Alto Cortex XDR. |
    | FQDN         | The FQDN from Palo Alto Cortex XDR. It is the `baseUrl` part of `baseUrl/public_api/v1/{name of api}/{name of call}/` |

2. Click the **Save** button to save your settings.

## Data Collected

### Logs

The Palo Alto Cortex XDR integration collects and forwards Palo Alto Cortex XDR incident and alert logs to Datadog.

### Metrics

The Palo Alto Cortex XDR integration does not include any metrics.

### Events

The Palo Alto Cortex XDR integration does not include any events.

## Support

Need help? Contact [Datadog Support][2].

[1]: https://docs-cortex.paloaltonetworks.com/p/XDR
[2]: https://docs.datadoghq.com/help/
