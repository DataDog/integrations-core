# Shopify

## Overview

[Shopify][1] is a comprehensive commerce platform designed to help individuals start, manage, and grow their businesses. It provides tools to build an online store, manage sales, market to customers, and accept payments in both digital and physical locations.

The Shopify Integration collects Event, Product, Customer and Order logs, sending them to Datadog for detailed analysis.

It includes dashboards that show and analyze logs, making it easier to monitor and understand patterns.

## Setup

### Configuration

The Shopify integration requires a Shopify Admin Account and a Custom app.
(Refer Steps to create a Shopify private app and access token below)

#### Steps to Create a Shopify Custom App and Obtain the Access Token
1. Log in to [Shopify][2] admin account and navigate to **Settings > Apps and sales channels**.
2. Select **Develop apps** and Click **Allow custom app development**.
3. Click **Create a custom app**, provide the necessary details and Click **Create app**.
4. Click **Configure Admin API Scopes** under the Overview tab.
5. In the **Admin API access scopes section**, select the following scope:
    - **read_orders** (Check the Request box)
    - **read_products** (Check the Request box)
    - **read_customers** (Check the Request box)
    - **read_content** (Check the Request box)
    - **read_price_rules** (Check the Request box)
6. Click **Save** to apply changes.
7. To get the api access token, Click **Install app**.
8. Under the **Admin API access token section**, Click **Reveal token once**.

#### Shopify DataDog integration configuration

Configure the Datadog endpoint to forward Shopify Logs to Datadog.

1. Navigate to the `Shopify` integration tile in Datadog.
2. Add your Shopify store credentials.

| Shopify parameters              | Description                                    |
| ------------------------------- | ---------------------------------------------  |
| Store Name                      | Store name of your Shopify admin account. It is the `xxxx` part of `https://admin.shopify.com/store/xxxx`.  |
| Access Token                    | Access Token for your Shopify admin account.     |

## Data Collected

### Logs 

The Shopify integration collects and forward Event, Product, Customer and Order logs to Datadog.

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
