# Greenhouse Integration For Datadog

## Overview

[Greenhouse][1] is a cloud-based hiring platform that helps companies manage their recruitment processes. It features job postings, application tracking, candidate communications, interview scheduling, offers, and bulk actions, all aimed at helping companies hire the right people efficiently.

This integration focuses on ingesting audit logs, which document important events and configuration changes, enabling teams to detect incidents and minimize their impact.

By seamlessly collecting these logs and channeling them into Datadog, the Greenhouse integration allows for comprehensive analysis. Leveraging the built-in logs pipeline, these logs are parsed and enriched, enabling effortless search and analysis. The integration provides insight into activities on the Greenhouse platform through the out-of-the-box dashboards.

## Setup

### Configuration

1. [Create an API key from the Greenhouse Platform](#greenhouse-configuration).
2. [Configure the Datadog endpoint to forward Greenhouse events as logs to Datadog](#greenhouse-integration-configuration).

#### Greenhouse Configuration

Steps to create API key on Greenhouse Platform:

1. Log in to **[Greenhouse][2]** with your credentials.
2. Click on the **Configure** button located in the top right corner.
3. Navigate to **Dev Center** in the left panel.
4. Select **API Credentials** from the left panel.
5. Click on **Create new API key**.
6. Choose **Harvest** for API type.
7. Select **Unlisted vendor** for Partner (if your name is not in the list).
8. Add a description for your API key.
9. Click on **Manage permissions**.
10. Be sure to copy and paste the API key as it cannot be retrieved later.
11. Under **Manage permissions**, check "Audit Log V1".
(**Note**: If this option is not available, contact Greenhouse support to enable the audit log feature.)
12. Click on **Save**.

#### Greenhouse Integration Configuration

Configure the Datadog endpoint to forward Greenhouse events as logs to Datadog.

1. Navigate to Greenhouse.
2. Add your Greenhouse API Key.

| Greenhouse Parameters | Description                                                                |
| ----------------------- | --------------------------------------------------------------------------|
| API Key                 | The Personal API key of Greenhouse  to authenticate the request          |

## Data Collected

### Logs

The integration collects and forwards Greenhouse audit logs to Datadog.

### Metrics

Greenhouse does not include any metrics.

### Service Checks

Greenhouse does not include any service checks.

### Events

Greenhouse does not include any events.

## Support

Need help? Contact [Datadog support][3].

[1]: https://www.greenhouse.com/
[2]: https://app.greenhouse.io/
[3]: https://docs.datadoghq.com/help/
