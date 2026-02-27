# HubSpot Content Hub

## Overview

[HubSpot Content Hub][1] is an all-in-one content marketing software that helps marketers create and manage content at scale. It helps create rich, expertise-backed content across various formats and channels.

The HubSpot Content Hub integration collects Activity Logs (audit, login, security) and Analytics Metrics (breakdown categories, content types), sending them to Datadog for detailed analysis. The logs are parsed and enriched for efficient searching, while the metrics provide insights into content performance.

Use Datadog [Reference Tables][5] to enrich your telemetry with metadata from HubSpot. You can map value fields to a primary key to automatically append these fields to logs or events containing that key.

The integration includes dashboards that show and analyze both Activity Logs and Analytics Metrics, making it easier to monitor and understand trends and issues.

## Setup

To integrate HubSpot with Datadog, Datadog connects to HubSpot using OAuth. The authenticated user must have owner permissions in the organizations that want to be integrated.

### Installation

1. Navigate to the [Integrations Page][2] and search for the "HubSpot Content Hub" integration.
2. Click the tile.
3. To add an account to install the integration, click the **Add Account** button.
4. Read the instructions in the modal and choose your telemetry and reference tables settings. Then, click the **Authorize** button, which redirects you to the HubSpot login page.
5. After logging in, you are prompted to select which HubSpot account you want to grant access to.
6. Click **Authorize**.
7. You're redirected back to Datadog's HubSpot tile with a new account. Datadog recommends changing the account name to something that is easier to remember. You can add multiple accounts with access to different organizations.

**Note**: HubSpot saves this authorization selection. To be prompted again or add new organizations, revoke app access in HubSpot (`User Preferences > Integrations > Connected Applications > Datadog - HubSpot OAuth App`), then restart the setup process.

## Data Collected

### Logs

The HubSpot Content Hub integration collects and forwards Activity logs to Datadog.

### Metrics

The HubSpot Content Hub integration collects and forwards Analytics metrics to Datadog.

{{< get-metrics-from-git "hubspot-content-hub" >}}

### Service Checks

The HubSpot Content Hub integration does not include any service checks.

### Events

The HubSpot Content Hub integration does not include any events.

### Reference Tables

[Reference Tables][5] allow you to automatically enrich and join your telemetry with additional fields from Companies defined in your HubSpot account.

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: https://www.hubspot.com/products/content
[2]: /integrations
[3]: https://app.hubspot.com/login
[4]: https://docs.datadoghq.com/help/
[5]: /reference-tables
