# HubSpot Content Hub

## Overview

[HubSpot Content Hub][1] is an all-in-one content marketing software that helps marketers create and manage content at scale. It helps create rich, expertise-backed content across various formats and channels.

The HubSpot Content Hub integration collects Activity Logs (audit, login, security) and Analytics Metrics (breakdown categories, content types), sending them to Datadog for detailed analysis. The logs are parsed and enriched for efficient searching, while the metrics provide insights into content performance.

The integration includes dashboards that show and analyze both Activity Logs and Analytics Metrics, making it easier to monitor and understand trends and issues.


## Setup

### Configuration

#### Get HubSpot Content Hub Credentials

1. Log in to [HubSpot Content Hub][2] 
2. Navigate to **Settings > Integrations > Private Apps**.
3. Click **Create private app**, and then enter the required information.
4. In the **Scopes** tab, click on **+Add New Scope**.
5. Select the checkboxes for the following scopes and click on **Update**:
   - **account-info.security.read**
   - **business-intelligence**
   - **content**
6. Click on **Create app**.
7. Review the details in the dialog box and click **Continue creating**.
8. In the success popup, click **Show Token**.

#### Add HubSpot Credentials

- HubSpot Access Token 


## Data Collected

### Logs 

The HubSpot Content Hub integration collects and forward Activity logs to Datadog.

### Metrics

The HubSpot Content Hub integration collects and forward Analytics metrics to Datadog.

### Service Checks

The HubSpot Content Hub integration does not include any service checks.

### Events

The HubSpot Content Hub integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: https://www.hubspot.com/products/content
[2]: https://app.hubspot.com/login
[3]: https://docs.datadoghq.com/help/
