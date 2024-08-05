# Cisco Identity Intelligence Integration For Datadog

## Overview

[Cisco Identity Intelligence][1] is an identity provider application that offers advanced security features for managing user identities and access across an organization's network. It enables organizations to authenticate, authorize, and monitor user access to applications and resources efficiently.Cisco Identity Intelligence helps organizations strengthen their security posture by providing robust identity and access management functionalities to protect against unauthorized access and security threats..

This integration ingests the following logs:

- Failed Checks

The Cisco Identity Intelligence integration seamlessly ingests the data of Cisco Identity Intelligence logs using the Webhook. Before ingestion of the data, it normalizes and enriches the logs, ensuring a consistent data format and enhancing information content for downstream processing and analysis. The integration provides insights into Failed checks through the out-of-the-box dashboards.

## Setup

### Configuration

#### Cisco Identity Intelligence Configuration

1. Go to [Cisco Identity Intelligence itegration][2] and carry out any necessary authentication steps. 
2. From left navigation check for integration if not selected then click on integrations.
3. Click **+ Add Integration** to create new integration.
4. Check for **Webhook** in the integration list.
5. Click on **+ Add Webhook Target** to create a webhook.
6. Provide the name of your webhook. 
7. In Webhook URL provides the URL (which will be used to receive logs) : https://http-intake.logs.datadoghq.com/api/v2/logs?ddsource=oort
8. In Authorization type select **API Key** and provide below details.
   - API key name: dd-api-key
   - API key value: <datadog api key> (which will be used to authorize above URL)
9. Click on save.
10. After configuring the webhook, proceed to select the newly created webhook for a specific check to start receiving logs for that particular check.
    - From the left navigation click on **Checks**.
    - In the reported channel column of checks click on edit and select your webhook to ingest particular check data into Datadog.

## Data Collected

### Logs

The Cisco Identity Intelligence integration collects and forwards Cisco Identity Intelligence Failed check logs to Datadog.

### Metrics

The Cisco Identity Intelligence integration does not include any metrics.

### Events

The Cisco Identity Intelligence integration does not include any events.

## Support

For further assistance, contact [Datadog Support][3].

[1]: https://docs.oort.io/
[2]: https://dashboard.oort.io/auth
[3]: https://docs.datadoghq.com/help/