# Cloudflare API Shield

## Overview

[Cloudflare API Shield][1] is a comprehensive solution designed to protect, manage, and monitor Application Programming Interfaces (APIs) against various security threats and operational challenges.

This integration collects HTTP request and API Shield Audit Logs, channeling them into Datadog for analysis. Leveraging the built-in logs pipeline, these logs are parsed and enriched, enabling search and analysis. The integration provides insight into HTTP request logs through out-of-the-box dashboards and includes ready-to-use Cloud SIEM detection rules for improved monitoring and security.

## Setup

### Generate API credentials in Cloudflare API Shield

1. Login into cloudflare dashboard using administrator account.
2. Go to **Manage Account** > **Account API Tokens**
3. Click **Create Token**.
4. In API Token templates, click on **Use template** for **Read all resources** option.
5. In the Zone Resources section, Select **All zones from an account** and select **account**.
6. Click on **Continue to summary**.
7. Click on **Create Token**.
8. Collect the **API token**.

### Collect Account ID in Cloudflare API Shield

1. Log in to the Cloudflare dashboard, and select your account.
2. The URL in your browser's address bar should show https://dash.cloudflare.com/ followed by a hex string. The hex string is your Cloudflare Account ID.

### Get Zone ID in Cloudflare API Shield
1. Login into cloudflare dashboard using administrator account.
2. Go to **Account home > Domains**.
3. Locate the domain (zone) for which you want to send the data.
4. Click the three-dot (ellipsis) menu next to the domain name to open its settings.
4. Copy the **Zone ID** for that domain.


### Connect your Cloudflare account to Datadog

1. Add your API Token, Account ID and Zones.

    | Parameters                            | Description                                                  |
    | ------------------------------------- | ------------------------------------------------------------ |
    | API Token                               | The API Token of Cloudflare account                          |
    | Account ID                            | Account ID of Cloudflare account                             |
    | Zones                                 | Select which zones to crawl (defaults to all zones). Enter a comma-separated list of zone IDs.                                                                      |

2. Click the **Save** button to save your settings.

## Data Collected

### Logs

The Cloudflare API Shield integration collects and forwards HTTP request and API Shield audit logs to Datadog.

### Metrics

The Cloudflare API Shield integration does not include any metrics.

### Events

The Cloudflare API Shield integration does not include any events.

## Support

Need help? Contact [Datadog support][2].

[1]: https://www.cloudflare.com/en-in/application-services/products/api-shield/
[2]: https://docs.datadoghq.com/help/
