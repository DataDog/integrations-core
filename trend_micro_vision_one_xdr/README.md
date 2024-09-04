## Overview

[Trend Micro Vision One XDR][1] collects and automatically correlates data across multiple security layers: email, endpoint, server, cloud workload, and network. This allows for faster detection of threats and improved investigation and response times through security analysis.

This integration ingests the following logs:

- Workbench Alerts: This endpoint contains information about all the standalone alerts triggered by detection models.
- Observed Attack Techniques: This endpoint contains information about observed attack techniques from Detections, Endpoint Activity, Cloud Activity, Email Activity, Mobile Activity, Network Activity, Container Activity, and Identity Activity data sources.

This integration collects all the above listed logs and sends them to Datadog for analysis. Datadog uses the built-in logs pipeline to parse and enrich these logs, enabling effortless search and analysis. The integration provides insight into workbench alerts and observed attack techniques through the out-of-the-box dashboards. Also, This integration provides out of the box detection rules.

## Setup

### Configuration

#### Create API KEY from Trend Micro Vision One XDR

1. On the Trend Vision One console, go to **Administration > API Keys** .
2. Generate a new authentication token. Click **Add API key**. Specify the settings of the new API key.
    - Name: A meaningful name that can help you identify the API key
    - Role: The user role assigned to the key. Select **SIEM** from dropdown.
    - Expiration time: The time the API key remains valid.
    - Status: Whether the API key is enabled.
    - Details: Extra information about the API key.
3. Click **Add**.
4. Copy and store the authentication token in a secure location.


#### Trend Micro Vision One XDR DataDog Integration Configuration

Configure the Datadog endpoint to forward Trend Micro Vision One XDR logs to Datadog.

1. Navigate to `Trend Micro Vision One XDR`.
2. Add your Trend Micro Vision One XDR credentials.

| Trend Micro Vision One XDR Parameters | Description                                                  |
| ------------------------------------- | ------------------------------------------------------------ |
| Host Region                           | The Region of your Trend Micro Vision One XDR Console        |
| API Key                               | The API Key of your Trend Micro Vision One XDR Console       |


## Data Collected

### Logs
The Trend Micro Vision One XDR integration collects and forwards Workbench Alerts and Observed Attack Techniques logs to Datadog.

### Metrics

Trend Micro Vision One XDR does not include any metrics.

### Service Checks

Trend Micro Vision One XDR does not include any service checks.

### Events

Trend Micro Vision One XDR does not include any events.

## Support

For further assistance, contact [Datadog Support][2].

[1]: https://www.trendmicro.com/en_in/business/products/detection-response/xdr.html
[2]: https://docs.datadoghq.com/help/

