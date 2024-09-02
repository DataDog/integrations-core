# GoDaddy

## Overview
GoDaddy is a web hosting and domain registration company that helps individuals and businesses establish their online presence. One of their key offerings is SSL certificate services. GoDaddy provides several types of SSL certificates, including Standard SSL for securing one site, Wildcard SSL for securing multiple subdomains, and advanced solutions for ecommerce sites requiring enhanced security.

The GoDaddy integration collects metrics from SSL certificates and their domains, directing them into Datadog for analysis. This integration provides data points such as the total number of certificates, issued certificates, expired certificates, revoked certificates, and domains associated with each certificate. It also includes specific metrics for certificates nearing expiration. All these metrics are accessible through out-of-the-box dashboards and monitors.

## Setup

### Get API credentials from GoDaddy

#### Find your GoDaddy API key and API secret

- Navigate to the [GoDaddy Developer Portal][1].
- Sign in with your GoDaddy account.
- Select "API Keys."
- Choose "Create New API Key."
- Provide a name for your API.
- Select "Production" under Environment.
- Click "Next." Your API Key is now created.
- Copy these credentials for the following configuration steps. Ensure they are stored securely and not exposed in public repositories or insecure locations.
- After storing your API Key and Secret, click on "Got It."

#### Find your GoDaddy customer number

- Go to your GoDaddy [Login & PIN page][2]. You might be prompted to sign in.
Under **Login Info**, find your **Customer number** (also known as your **shopper ID**).

### GoDaddy Datadog Integration Configuration

Configure the Datadog endpoint to forward GoDaddy metrics to Datadog.

1. Navigate to `GoDaddy`.
2. Add your GoDaddy credentials.

| GoDaddy parameters               | Description                            |
|----------------------------------|----------------------------------------|
| GoDaddy API key                  | The API key of GoDaddy.                |
| GoDaddy secret key               | The secret key of GoDaddy              |
| GoDaddy customer number          | The GoDaddy customer number (or shopper ID) |

## Data Collected

### Logs

The GoDaddy integration does not include any logs.

### Metrics

The GoDaddy integration collects and forwards Certificates and their Domains metrics to Datadog. See [metadata.csv][5] for a list of metrics provided by this integration.

### Events

The GoDaddy integration does not include any events.

## Support

For further assistance, contact [Datadog Support][4].

[1]: https://developer.godaddy.com/
[2]: https://sso.godaddy.com/security
[3]: https://developer.godaddy.com/doc/
[4]: https://docs.datadoghq.com/help/
[5]: https://github.com/DataDog/integrations-core/blob/master/godaddy/metadata.csv
