# Cisco Umbrella DNS Integration for Datadog

## Overview

[Cisco Umbrella][1] is the leading platform for network DNS security monitoring. Umbrella's DNS-layer security offers a fast and easy way to enhance security, providing improved visibility and protection for users both on and off the network. By preventing threats over any port or protocol before they reach the network or endpoints, Umbrella DNS-layer security aims to deliver the most secure, reliable, and fastest internet experience to over 100 million users.

Cisco Umbrella DNS integration ingests DNS and Proxy logs to Datadog.  Datadog integration log pipeline enriches logs to include geo-graphical information of client and server hosts and normalizes data to datadog standard attributes. This integration offers visualizations and provides detailed insights into DNS traffic and proxied requests, including total DNS requests, allowed/blocked domains, top blocked categories, proxied traffic over time, and more via dashboards.

## Setup

### Configuration

#### Cisco Umbrella DNS Configuration

1. Login to [**Umbrella** > **Login**][2] with your credentials.
2. From the left panel, click on **Admin**.
3. Then, click on **API Keys**.
4. Create a new API Key using the **Add** button.
5. Apply `reports.aggregations:read` and `reports.granularEvents:read` key scopes to the API key.
6. Copy the API Key and Key Secret.

#### Cisco Umbrella DNS DataDog Integration Configuration

Configure the Datadog endpoint to forward Cisco Umbrella DNS events as logs to Datadog.

1. Navigate to `Cisco Umbrella DNS`.
2. Provide your Cisco Umbrella DNS credentials and click on `Add`.

| Cisco Umbrella DNS Parameters | Description                                                                |
| ----------------------------- | -------------------------------------------------------------------------- |
| API Key                       | The API Key from Cisco Umbrella.                                           |
| Key Secret                    | The Key Secret from Cisco Umbrella.                                        |

## Data Collected

### Logs

The integration collects and forwards Cisco Umbrella DNS and Proxy logs to Datadog.

### Metrics

The Cisco Umbrella DNS integration does not include any metrics.

### Events

The Cisco Umbrella DNS integration does not include any events.

## Support

For further assistance, contact [Datadog Support][3].

[1]: https://umbrella.cisco.com/
[2]: https://login.umbrella.com/
[3]: https://docs.datadoghq.com/help/
