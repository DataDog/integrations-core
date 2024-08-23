# GoDaddy

## Overview
GoDaddy is a prominent web hosting and domain registration company that provides a variety of services to help individuals and businesses establish their online presence. A notable aspect of GoDaddy product lineup is their SSL certificate services. GoDaddy offers a range of SSL certificate options to suit different needs, including standard SSL for securing one site, Wildcard SSL for securing multiple subdomains, and more advanced solutions for ecommerce sites requiring the highest level of security.

The GoDaddy integration seamlessly collects metrics from SSL certificates and domains, directing them into Datadog for analysis. This integration provides insights including total certificates, issued certificates, expired certificates, revoked certificates, count of domains associated with each certificate. It features statistics for certificates that are about to expire along with many additional metrics, all accessible through out-of-the-box dashboards and monitors.


## Setup

### Get API Credentials from GoDaddy

#### GoDaddy API KEY and API Secret

- Go to [Godaddy Developer Portal][1]
- Sign in with your GoDaddy account.
- Select "API Keys".
- Choose "Create New API Key".
- Provide a name for your API.
- Select "Production" under Environment.
- Click "Next".
- Your API Key is now created.
- Copy these credentials for the subsequent configuration steps.
- Ensure these credentials are stored securely and not exposed in public repositories or insecure locations.
- After preserving your API Key and Secret in a separate document, click on "Got It".

#### Godaddy Customer Number (ShopperID)

- Go to your GoDaddy [Login & PIN page][2]. You might be prompted to sign in.
- Under Login Info, find your Customer number(ShopperId).

### Godaddy Datadog Integration Configuration

Configure the Datadog endpoint to forward GoDaddy metrics to Datadog.

1. Navigate to `GoDaddy`.
2. Add your GoDaddy credentials.

| GoDaddy Parameters               | Description                            |
|----------------------------------|----------------------------------------|
| GoDaddy API key                  | The API key of GoDaddy.                |                                                    |
| GoDaddy Secret Key               | The Secret Key of GoDaddy              |
| GoDaddy Customer Number          | The GoDaddy Customer Number(ShopperId) |

## Data Collected

### Logs

The GoDaddy integration does not include any logs.

### Metrics

The GoDaddy integration collects and forwards Certificates and Domains metrics to Datadog. See [metadata.csv][5] for a list of metrics provided by this integration.

### Events

The GoDaddy integration does not include any events.

## Support

For further assistance, contact [Datadog Support][4].

[1]: https://developer.godaddy.com/
[2]: https://sso.godaddy.com/security
[3]: https://developer.godaddy.com/doc/
[4]: https://docs.datadoghq.com/help/
[5]: https://github.com/DataDog/integrations-core/blob/master/godaddy/metadata.csv