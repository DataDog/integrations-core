# Palo Alto Cortex XDR Integration For Datadog

## Overview

[Palo Alto Cortex XDR][1] is a comprehensive detection and response platform that provides advanced threat protection across endpoints, networks, and cloud environments. It integrates endpoint protection, network security, and analytics to offer real-time visibility and response capabilities to combat sophisticated cyber threats effectively.

This integration ingests the following logs:

- Incident
- Alert

The Palo Alto Cortex XDR integration seamlessly collect the data of Palo Alto Cortex XDR logs using the REST APIs.
Before ingestion of the data, it normalizes and enriches the logs, ensuring a consistent data format and enhancing information content for downstream processing and analysis. The integration provides insights into incidents and alerts through the out-of-the-box dashboards.

## Setup

### Configuration

#### Get Credentials of Palo Alto Cortex XDR

#### Steps to create API key

1. Sign in into the [**Palo Alto Cortex XDR**][2]
2. Navigate to **Settings** > **Configurations** > **Integrations** > **API Keys**
3. Click on **+ New Key**
4. Choose the type of API Key based on your desired security level **Advanced** or **Standard**
5. If you want to define a time limit on the API key authentication, check **Enable Expiration Date** and select the **expiration date and time**. Navigate to **Settings** > **Configurations** > **Integrations** > **API Keys** to track the Expiration Time field for each API key
6. Provide a comment that describes the purpose for the API key, if desired.
7. Select the desired level of access for this key from existing **Roles**, or you can select **Custom** to set the permissions on a more granular level
8. Click on **Generate** to generate the API Key.
9. Copy the API key, and then click **Done**. This value represents your unique **Authorization:{key}**

#### Steps to get Cortex XDR API Key ID

1. In the API Keys table, locate the ID field.
2. Note your corresponding ID number. This value represents the **x-xdr-auth-id:{key_id}** token.

#### Steps to get FQDN

1. Right-click your API key and select **View Examples**.
2. Copy the **CURL Example** URL. The example contains your unique **FQDN**.

#### Palo Alto Cortex XDR DataDog Integration Configuration

Configure the Datadog endpoint to forward Palo Alto Cortex XDR logs to Datadog.

1. Navigate to `Palo Alto Cortex XDR`.
2. Add your Palo Alto Cortex XDR credentials.

| Palo Alto Cortex XDR Parameters | Description  |
| ------------------------------- | ------------ |
| API key                         | The API key from Palo Alto Cortex XDR. |
| API Key ID                      | The auth id from Palo Alto Cortex XDR. |
| FQDN                            | The FQDN from Palo Alto Cortex XDR. It is the `baseUrl` part of `baseUrl/public_api/v1/{name of api}/{name of call}/` |

## Data Collected

### Logs

The Palo Alto Cortex XDR integration collects and forwards Palo Alto Cortex XDR Incident and alert logs to Datadog.

### Metrics

The Palo Alto Cortex XDR integration does not include any metrics.

### Events

The Palo Alto Cortex XDR integration does not include any events.

## Support

For further assistance, contact [Datadog Support][3].

[1]: https://docs-cortex.paloaltonetworks.com/p/XDR
[2]: https://sso.paloaltonetworks.com/
[3]: https://docs.datadoghq.com/help/
