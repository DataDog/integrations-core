# Shopify

## Overview

[Shopify][1] is a comprehensive commerce platform designed to help individuals start, manage, and grow their businesses. It provides tools to build an online store, manage sales, market to customers, and accept payments in both digital and physical locations.

The Shopify Integration collects Event, Product, Customer, and Order logs, sending them to Datadog for detailed analysis.

It includes dashboards that show and analyze logs, making it easier to monitor and understand patterns.

## Setup

### Generate OAuth credentials in Shopify

1. Log in to [Shopify][2] admin account.
2. The **Shopify Store name** is the `xxxx` part of the Store URL (`https://admin.shopify.com/store/xxxx`).
3. Open the [Shopify Dev Dashboard][4].
4. Click **Create app**.
5. In **Start from Dev Dashboard**, enter an **App name**, and click **Create**.
6. After the app is created, go to the **Versions** tab and click **Create a version**:
   - Define the **App URL** `https://shopify.dev/apps/default-app-home`.
   - Under Access > Scope select the following scopes:
     - **read_orders**
     - **read_products**
     - **read_customers**
     - **read_content**
     - **read_price_rules**
7. Click **Release**.
8. In the **Release this new version?** pop-up, click **Release**.
9. Install the app on your store:
    - Click on app name to go to the **Overview** tab of the app.
    - Click **Install app**.
    - Select your store and click on **Install** to confirm installation.
10. After installation, open the **Settings** tab of the app in Dev dashboard.
11. Copy the **Client ID** and **Secret**.

### Connect your Shopify account to Datadog
1. Add your Store Name and Access Token
    |Parameters|Description|
    |--------------------|--------------------|
    |Store Name|Store name of your Shopify admin account.|
    |Client ID|Client ID of the shopify app (Required for OAuth authentication).|
    |Client Secret|Secret of the shopify app (Required for OAuth authentication).|
    |Access Token|Access Token for your Shopify admin account (Required for legacy API access token authentication).|
    
2. Click the **Save** button to save your settings.

## Data Collected

### Logs

The Shopify integration collects and forwards Event, Product, Customer, and Order logs to Datadog.

### Metrics

The Shopify integration does not include any metrics.

### Service Checks

The Shopify integration does not include any service checks.

### Events

The Shopify integration does not include any events.

## Troubleshooting

This integration is not managed by Shopify. For assistance, please contact
[Datadog support][3].

[1]: https://www.shopify.com/
[2]: https://www.shopify.com/in/store-login
[3]: https://docs.datadoghq.com/help/
[4]: https://dev.shopify.com/dashboard/
