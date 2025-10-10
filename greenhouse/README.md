# Greenhouse

## Overview

[Greenhouse][1] is a cloud-based hiring platform that helps companies manage their recruitment processes. It features job postings, application tracking, candidate communications, interview scheduling, offers, and bulk actions, all aimed at helping companies hire the right people efficiently.

This integration ingests the following logs:

- Audit: Represents important events and configuration changes, enabling teams to detect incidents and minimize their impact.

The Greenhouse integration collects these logs and sends them to Datadog. These logs are parsed and enriched through the built-in logs pipeline, which enables search and analysis. The integration also provides insight into activities on the Greenhouse platform through the out-of-the-box dashboards.

## Setup

### Generate API credentials in Greenhouse

1. Log in to **[Greenhouse account][2]**.
2. Click **Configure** located in the top right corner.
3. Navigate to **Dev Center** in the left panel.
4. Select **API Credentials**.
5. Click **Create new API key**.
6. Choose **Harvest** for API type.
7. Select **Unlisted vendor** for a Partner (if your name is not in the list).
8. Add a description for your API key.
9. Click **Manage permissions**.
10. Under **Manage permissions**, check "Audit Log V1".
(**Note**: If this option is not available, contact **[Greenhouse support][4]** to enable the audit log feature.)
11. Click **Save**.

### Connect your Greenhouse Account to Datadog

1. Add your Greenhouse API Key.

    | Parameters | Description                                                    |
    | -----------| ---------------------------------------------------------------|
    | API Key    | The Personal API key of Greenhouse to authenticate the request |

2. Click the Save button to save your settings.

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
[4]: https://support.greenhouse.io/hc/en-us
