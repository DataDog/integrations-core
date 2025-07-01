# Proofpoint On-Demand

## Overview

[Proofpoint On-Demand][1] helps organizations detect, classify, and mitigate email threats in real-time, securing and managing email communications.

This integration ingests the following logs:

- Message Logs: These logs contain detailed information about email traffic.

This integration seamlessly collects message logs, channeling them into Datadog for analysis. Leveraging the built-in logs pipeline, these logs are parsed and enriched, enabling effortless search and analysis. The integration provides insights into message logs through the out-of-the-box dashboards and includes ready-to-use Cloud SIEM detection rules for improved monitoring and security.

## Setup

### Get an API key from the Proofpoint On-Demand Portal

1. Log in to the Proofpoint Admin portal.
2. Go to **Settings > API Key Management**.
3. Under **PoD Logging**, click **Create New** to generate a new API key.
4. Enter a unique name for the API key.
5. Copy **Cluster ID**.
6. Click **Generate Key**.
7. After generating the key, select **View Details** from the menu of the new API key.
8. Copy the generated API key.


### Connect your Proofpoint On-Demand Account to Datadog

1. Add your Proofpoint On-Demand Credentials.

    | Parameters                            | Description                                                  |
    | ------------------------------------- | ------------------------------------------------------------ |
    | Cluster ID                            | The Cluster ID of your Proofpoint On-Demand account          |
    | API Key                             | The API Key of your Proofpoint On-Demand account           |

2. Click the **Save** button to save your settings.

## Data Collected

### Logs

The Proofpoint On-Demand integration collects and forwards message logs to Datadog.

### Metrics

The Proofpoint On-Demand integration does not include any metrics.

### Events

The Proofpoint On-Demand integration does not include any events.

## Support

Need help? Contact [Datadog support][2].

[1]: https://www.proofpoint.com/us/products/email-security-and-protection/email-protection
[2]: https://docs.datadoghq.com/help/