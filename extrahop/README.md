# ExtraHop Integration For Datadog

## Overview

[ExtraHop][1] leverages the network to give organizations comprehensive visibility into the cyber threats, vulnerabilities, and performance issues that evade their existing security and IT tools.

This integration ingests the following log:

- Detection: Represents data of anomalous behavior identified by ExtraHop system.
- Investigation: Represents a collection of data related to a specific security investigation, including its status, assignment, and associated detections.

The ExtraHop integration seamlessly collect the data of ExtraHop logs using REST APIs.
Before ingesting the data, it normalizes and enriches the logs, ensuring a consistent data format and enhancing information content for downstream processing and analysis. The integration provides insights into Detections using out-of-the-box dashboards.

## Setup

### Configuration

#### Get Credentials of ExtraHop

#### Steps to create Client ID and Client Secret

1. Login to **ExtraHop** Platform with your credentials.
2. From ExtraHop Platform, go to **System Settings** > **API Access** > **REST API Credentials**.
3. Then, click **Create Credentials**.
4. In the **Create Rest API credentials** section, provide credential name, select the appropriate system access, select the appropriate access for NDR Module Access, NPM Module Access, Packet And Session Key Access and click save button. The **Copy REST API Credentials** section for this credential is displayed.
5. Copy the **ID** and **Secret**.

#### ExtraHop DataDog Integration Configuration

Configure the Datadog endpoint to forward ExtraHop logs to Datadog.

1. Navigate to `ExtraHop`.
2. Add your ExtraHop credentials.

| ExtraHop Parameters             | Description  |
| ------------------------------- | ------------ |
| Domain                          | Domain of ExtraHop platform. |
| Client ID                       | The Client ID from ExtraHop. |
| Client Secret                   | The Client Secret from ExtraHop. |

## Data Collected

### Logs

The ExtraHop integration collects and forwards ExtraHop Detection and investigation logs to Datadog.

### Metrics

The ExtraHop integration does not include any metrics.

### Events

The ExtraHop integration does not include any events.

## Support

Need help? Contact [Datadog support][2].

[1]: https://docs.extrahop.com/current/
[2]: https://docs.datadoghq.com/help/