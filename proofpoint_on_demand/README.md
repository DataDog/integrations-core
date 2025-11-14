# Proofpoint On-Demand

## Overview

[Proofpoint On-Demand][1] helps organizations detect, classify, and mitigate email threats in real-time, securing and managing email communications.

This integration ingests the following logs:

- Message Logs: These logs contain detailed information about email traffic.

This integration collects message logs and send them to Datadog for analysis. The logs are parsed and enriched using Datadog's built-in pipeline, which allows for searching and analysis. Dashboards and Cloud SIEM detection rules are included to help monitor message logs and improve security.

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

1. Add your Proofpoint On-Demand credentials.

    | Parameters                            | Description                                                  |
    | ------------------------------------- | ------------------------------------------------------------ |
    | Cluster ID                            | The Cluster ID for your Proofpoint On-Demand account         |
    | API key                               | The API key for your Proofpoint On-Demand account           |

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
