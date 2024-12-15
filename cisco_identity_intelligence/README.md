# Cisco Identity Intelligence Integration For Datadog

## Overview

[Cisco Identity Intelligence][1] is an identity provider application that offers advanced security features for managing user identities and access across an organization's network. It enables organizations to authenticate, authorize, and monitor user access to applications and resources efficiently. Cisco Identity Intelligence helps organizations strengthen their security posture by providing robust identity and access management functionalities to protect against unauthorized access and security threats.

This integration ingests the following logs:

- Failed Checks

The Cisco Identity Intelligence integration seamlessly ingests the data of Cisco Identity Intelligence logs using the webhook. Before ingestion of the data, it normalizes and enriches the logs, ensuring a consistent data format and enhancing information content for downstream processing and analysis. The integration provides insights into failed checks through out-of-the-box dashboards.

## Setup

### Configuration

#### Cisco Identity Intelligence Configuration

1. Go to the [Cisco Identity Intelligence integration][2] and follow any necessary authentication steps.
2. From the left navigation, check for the integration. If it's not selected, then click Integrations.
3. Click **+ Add Integration** to create an integration.
4. Check for **Webhook** in the integration list.
5. Click **+ Add Webhook Target** to create a webhook.
6. Provide the name of your webhook.
7. In the Webhook URL field, provide the URL (which is used to receive logs): `https://http-intake.logs.datadoghq.com/api/v2/logs?ddsource=oort`.
8. In the Authorization type field, select **API Key** and provide the following details:
   - API key name: `dd-api-key`
   - API key value: <YOUR_DATADOG_API_KEY> (which is used to authorize the URL above)
9. Click Save.
10. After configuring the webhook, select the newly created webhook for a specific check to start receiving logs for that particular check.
    - From the left navigation, click **Checks**.
    - In the reported channel column of checks, click Edit and select your webhook to ingest particular check data into Datadog.

## Data Collected

### Logs

The Cisco Identity Intelligence integration collects and forwards Cisco Identity Intelligence failed check logs to Datadog.

### Metrics

The Cisco Identity Intelligence integration does not include any metrics.

### Events

The Cisco Identity Intelligence integration does not include any events.

## Support

For further assistance, contact [Datadog Support][3].

[1]: https://docs.oort.io/
[2]: https://dashboard.oort.io/auth
[3]: https://docs.datadoghq.com/help/