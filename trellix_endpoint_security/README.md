## Overview

[Trellix Endpoint Security (ENS)][1] protects servers, computer systems, laptops, and tablets against known and unknown threats. These threats include malware, suspicious communications, unsafe websites, and downloaded files. Trellix Endpoint Security enables multiple defense technologies to communicate in real time to analyze and protect against threats.

This integration ingests the following logs:

- **Threat Events**: This endpoint provides details about threat events triggered by Trellix Endpoint Security, including threat prevention, web control, firewall, and adaptive threat protection.

This integration provides enrichment and visualization for above mentioned event types. It helps to visualize detailed insights into security trends, threats, and policy violations through the out-of-the-box dashboards. Also, This integration provides out of the box detection rules.

**Minimum Agent version:** 7.57.2

## Setup

### Generate API Credentials in Trellix Endpoint Security

1. Log in to the Trellix ePO Saas.
2. Navigate to the **[Client Credentials][2]** page.
3. Click **Add** at the top right of the page.
4. From the **Scopes** menu, select `epo.evt.r`, which is listed in front of `Events`.
5. Click **Create**.
6. Copy the `Client ID`, `Client Secret`, and `API Key`.

### Connect your Trellix Endpoint Security Account to Datadog

1. Add your Client ID, Client Secret, and API Key.
   | Parameters    | Description                            |
   | ------------- | -------------------------------------- |
   | Client ID     | The Client ID of Trellix ePO SaaS.     |
   | Client Secret | The Client Secret of Trellix ePO SaaS. |
   | API Key       | The API Key of Trellix ePO SaaS.       |

2. Click the Save button to save your settings.

## Data Collected

### Logs

The Trellix Endpoint Security integration collects and forwards events related to threat prevention, web control, firewall, and adaptive threat protection to Datadog.

### Metrics

The Trellix Endpoint Security integration does not include any metrics.

### Events

The Trellix Endpoint Security integration does not include any events.

## Support

For additional assistance, contact [Datadog support][3].

[1]: https://www.trellix.com/products/endpoint-security/
[2]: https://uam.ui.trellix.com/clientcreds.html
[3]: https://docs.datadoghq.com/help/
