# HubSpot Content Hub

## Overview

[HubSpot Content Hub][1] is an all-in-one content marketing software that helps marketers create and manage content at scale. It helps create rich, expertise-backed content across various formats and channels.

The HubSpot Content Hub integration collects Activity Logs (audit, login, security) and Analytics Metrics (breakdown categories, content types), sending them to Datadog for detailed analysis. The logs are parsed and enriched for efficient searching, while the metrics provide insights into content performance.

The integration includes dashboards that show and analyze both Activity Logs and Analytics Metrics, making it easier to monitor and understand trends and issues.


## Setup

### Configuration

The HubSpot Content Hub Integration requires a HubSpot Content Hub Enterprise Account and a Private app. 

#### Create a HubSpot Private App and Obtain an Access Token

1. Log in to [HubSpot Content Hub][2] and navigate to **Settings > Integrations > Private Apps**.
2. Click **Create private app**, and then enter the required information.
3. On the **Scopes** tab, select the **Request** checkbox for the following scopes:
   - **account-info.security.read**
   - **business-intelligence**
   - **content**
4. Click **Create app**.
5. Review the details in the dialog box and click **Continue creating**.
6. In the success popup, click **Show Token**, and then click **Copy** to use the access token.
7. To view the token later, go to the list of private apps, find the created app, and select **View access token**.


#### Configure the HubSpot Content Hub integration in Datadog

Configure the Datadog endpoint to forward HubSpot Content Hub logs and metrics to Datadog.

1. Navigate to the `HubSpot Content Hub` integration tile in Datadog.
2. Add your HubSpot Content Hub credentials.

| HubSpot Content Hub parameters | Description                                    |
| ------------------------------ | ---------------------------------------------  |
| Access Token                   | Access token for your HubSpot private app.     |


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
