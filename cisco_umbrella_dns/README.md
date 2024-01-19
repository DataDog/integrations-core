# Cisco Umbrella DNS Integration for Datadog

## Overview

[Cisco Umbrella][1] is the leading platform for network DNS security monitoring. Umbrella's DNS-layer security offers a fast and easy way to enhance security, providing improved visibility and protection for users both on and off the network. By preventing threats over any port or protocol before they reach the network or endpoints, Umbrella DNS-layer security aims to deliver the most secure, reliable, and fastest internet experience to over 100 million users.

The Cisco Umbrella DNS integration collects DNS and Proxy logs and sends them to Datadog. Using the out-of-the-box logs pipeline, the logs are parsed and enriched for easy searching and analysis. This integration includes several dashboards visualizing total DNS requests, allowed/blocked domains, top blocked categories, proxied traffic over time, and more. If you have Datadog Cloud SIEM, Umbrella DNS logs will be analyzed by threat intelligence for matches against common attacker destinations. DNS logs are also useful for threat hunting and during investigations to compliment logs from other sources.

## Setup

### Configuration

#### Cisco Umbrella DNS Configuration

1. Login to [**Umbrella**][2] with your credentials.
2. From the left panel, select **Admin**.
3. Select **API Keys**.
4. Create a new API Key.
5. Apply the `reports.aggregations:read` and `reports.granularEvents:read` key scopes to the API key.
6. Copy the API Key and Key Secret, which will be used during the next portion of configuration steps.

#### Cisco Umbrella DNS DataDog Integration Configuration

Configure the Datadog endpoint to forward Cisco Umbrella DNS events as logs to Datadog.

1. Navigate to `Cisco Umbrella DNS`.
2. Add your Cisco Umbrella DNS credentials.

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
