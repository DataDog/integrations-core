# ExtraHop

## Overview

[ExtraHop][1] applies machine learning techniques and rule-based monitoring to your wire data to identify unusual behaviors and potential risks to the security and performance of your network.

This integration ingests the following logs:

- Detection: Represents data of anomalous behavior identified by ExtraHop system.
- Investigation: Represents a collection of data related to a specific security investigation, including its status, assignment, and associated detections.

This integration seamlessly collects all the above listed logs, channeling them into Datadog for analysis. Leveraging the built-in logs pipeline, these logs are parsed and enriched, enabling effortless search and analysis. The integration provides insight into detections and investigations through the out-of-the-box dashboards.

**Minimum Agent version:** 7.58.2

## Setup

### Generate API credentials in ExtraHop

1. Log in to the ExtraHop platform.
2. Go to **System Settings** > **API Access** and click **Create Credentials** which is at the bottom of the page under **Rest API Credentials** section.
3. Navigate to **System Settings** > **API Access** > **Rest API Credentials**. In the top right corner, click **Create Credentials** and specify the settings of the new Client ID and Client Secret.
    - Name: A meaningful name that can help you identify the Client ID and Client Secret.
    - System Access: The system access permission assigned to the ID and Secret. Select **Full read-only**.
    - NDR Module Access: The NDR module access permission assigned to the ID and Secret. Select **Full Access**.
    - NPM Module Access: The NPM module access permission assigned to the ID and Secret. Select **No Access**.
    - Packet And Session Key Access: The packet and session key access permission assigned to the ID and Secret. Select **No Access**.
4. Click **Save**.

### Connect your ExtraHop Account to Datadog

1. Add your ExtraHop credentials.

    | ExtraHop Parameters                   | Description                                                  |
    | ------------------------------------- | ------------------------------------------------------------ |
    | Subdomain                            | The subdomain of your ExtraHop Console                      |
    | Client ID                             | The Client ID of your ExtraHop Console                       |
    | Client Secret                         | The Client Secret of your ExtraHop Console                   |

2. Click the Save button to save your settings.

## Data Collected

### Logs

The ExtraHop integration collects and forwards ExtraHop detection and investigation logs to Datadog.

### Metrics

The ExtraHop integration does not include any metrics.

### Service Checks

ExtraHop does not include any service checks.

### Events

The ExtraHop integration does not include any events.

## Support

Need help? Contact [Datadog support][2].

[1]: https://docs.extrahop.com/current/
[2]: https://docs.datadoghq.com/help/