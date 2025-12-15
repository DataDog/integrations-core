## Overview

[Vectra][1] provides a platform for detecting, investigating, and responding to advanced threats across hybrid environments.

This integration ingests the following logs:

- **Detections**: Detections provide detailed information on security events detected within the Vectra platform, with events generated upon the initial detection and each subsequent update.
- **Entity Scoring Events**: Entity Scoring Events provide detailed information on changes to an entity's score, which occur upon initial threat detection, the discovery of additional detections, and updates to any previously discovered detections.
- **Audit Events**: Audit Events provide detailed information on user actions performed within the system.

Integrate Vectra with Datadog to gain insights into detections, entity scoring events and audit events using pre-built dashboard visualizations. Datadog uses its built-in log pipelines to parse and enrich these logs, facilitating easy search and detailed insights. Additionally, the integration can be used for Cloud SIEM detection rules for enhanced monitoring and security.

## Setup

### Obtaining Client Credentials

1. Log into Vectra Platform and navigate to **Configuration** > **Access** > **API Clients**.
2. Click **Add API Client** and configure the following parameters:
   - Client Name: A user-friendly name to identify the client
   - Role: Choose **Auditor**
3. Click **Generate Credentials** and copy the Client ID and Secret Key for later use.
4. Identify your Sub Domain by checking the hostname suffix of your Vectra Platform URL. For example, `<example>.portal.vectra.ai` is your platform URL then `example` is your Sub Domain.

### Connect your Vectra Account to Datadog

1. Add your `Sub Domain`, `Client ID` and `Secret Key`.
   | Parameters | Description |
   | ---------- | ---------------------------------------------- |
   | Sub Domain | The Sub Domain from Vectra Platform URL |
   | Client ID | The Client ID of your Vectra Platform |
   | Secret Key | The Secret Key of your Vectra Platform |
   | Get Detections | Control the collection of Detections from Vectra. <br> Enabled by default.|
   | Get Entity Scoring Events | Control the collection of Entity Scoring Events from Vectra. <br> Enabled by default.|
   | Get Audit Events | Control the collection of Audit Events from Vectra. <br> Enabled by default.|
2. Click the Save button to save your settings.

## Data Collected

### Logs

Vectra collects and forwards detections, entity scoring events and audit events to Datadog.

### Metrics

Vectra does not include any metrics.

### Events

Vectra does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][2].

[1]: https://www.vectra.ai/
[2]: https://docs.datadoghq.com/help/
