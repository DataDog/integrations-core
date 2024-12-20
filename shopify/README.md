# Shopify

## Overview

[Shopify][1] is a comprehensive commerce platform designed to help individuals start, manage, and grow their businesses. It provides tools to build an online store, manage sales, market to customers, and accept payments in both digital and physical locations.

The Shopify Integration collects Event, Product, Customer, and Order logs, sending them to Datadog for detailed analysis.

It includes dashboards that show and analyze logs, making it easier to monitor and understand patterns.

## Setup

### Generate API credentials in Shopify
1. Log in to [Shopify][2] admin account.
2. The Shopify Store name is the `xxxx` part of the Store URL (`https://admin.shopify.com/store/xxxx`).
3. Navigate to **Settings > Apps and sales channels**.
4. Select **Develop apps** and click **Allow custom app development**.
5. Click **Create a custom app**, provide the necessary details and click **Create app**.
6. Click **Configure Admin API Scopes** under the Overview tab.
7. In the **Admin API access scopes section**, select the following scopes:
    - **read_orders** 
    - **read_products** 
    - **read_customers** 
    - **read_content** 
    - **read_price_rules** 
8. Click **Save** to apply the changes.
9. Click **Install app** and get the **Access Token** from the **Admin API access token** section.

### Connect your Shopify account to Datadog
1. Add your Store Name and Access Token
    |Parameters|Description|
    |--------------------|--------------------|
    |Store Name|Store name of your Shopify admin account.|
    |Access Token|Access Token for your Shopify admin account.|
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

Need help? Contact [Datadog support][3].

[1]: https://www.shopify.com/
[2]: https://www.shopify.com/in/store-login
[3]: https://docs.datadoghq.com/help/
