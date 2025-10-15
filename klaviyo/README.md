# Klaviyo

## Overview

[Klaviyo][1] is a cloud-based email and SMS marketing automation platform supporting integrations with major eCommerce, ads, and CRM platforms.

Integrate Klaviyo with Datadog to gain insights into marketing campaign communication and track eCommerce performance based on Klaviyo events.

**Minimum Agent version:** 7.68.1

## Setup

Follow the instructions below to configure this integration for Klaviyo Marketing and eCommerce events.

### Configuration

#### Install Datadog Integration in Klaviyo
Within your Klaviyo account, first add the Datadog integration. The integration allows Datadog
to see Klaviyo events and metrics via the Klaviyo API.

1. Log in to your [Klaviyo account][2].
2. In the left-side panel, navigate to **Integrations**.
3. Click **Add integrations**.
4. Search for Datadog and click on the tile.
5. Click **Install**. 
6. Navigate to Datadog, then log in.

#### Install Klaviyo Integration in Datadog
After the above installation within Klaviyo is performed, complete the Datadog integration by clicking 
**Install Integration** which guides you through an authorization process with Klaviyo.

The authorization process will include an approval dialog which asks to give Datadog permission to
read Klaviyo events and metrics. The scopes involved for this
access are "accounts:read metrics:read events:read" and nothing more.

## Data Collected

### Logs
The Klaviyo integration forwards the marketing and eCommerce events as logs to Datadog.

### Metrics

Klaviyo does not include any metrics.

### Service Checks

Klaviyo does not include any service checks.

### Events

Klaviyo does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: https://www.klaviyo.com/
[2]: https://www.klaviyo.com/login
[3]: https://docs.datadoghq.com/help/

