## Overview

[Trend Micro Vision One XDR][1] collects and automatically correlates data across multiple security layers: email, endpoint, server, cloud workload, and network. This enables faster threat detection, enhances investigation and response times through improved security analysis.

This integration ingests the following logs:

- **Workbench Alerts**: This endpoint contains information about all the standalone alerts triggered by detection models.
- **Observed Attack Techniques**: This endpoint contains information about observed attack techniques from Detections, Endpoint Activity, Cloud Activity, Email Activity, Mobile Activity, Network Activity, Container Activity, and Identity Activity data sources.

This integration collects logs from the sources listed above and sends them to Datadog for analysis with our Log Explorer and Cloud SIEM products
* [Log Explorer][3]
* [Cloud SIEM][4]

## Setup

### Generate API Credentials in Trend Micro Vision One XDR

1. In the Trend Vision One console, go to on the left side-bar menu and visit **Administration > API Keys**.
2. Generate a new authentication token. Click **Add API key**. Specify the settings of the new API key with the following:
    - **Name**: A meaningful name that can help you identify the API key
    - **Role**: The user role assigned to the key. Select **SIEM** from dropdown.
    - **Expiration time**: The time the API key remains valid.
    - **Status**: Whether the API key is enabled.
    - **Details**: Extra information about the API key.
3. Click **Add**.
4. To identify the Host Region of your Trend Micro Vision One XDR console please refer [here][5].

### Connect your Trend Micro Vision One XDR Account to Datadog

1. Add your Host Region and API Key.
    | Parameters  | Description                                             |
    | ----------- | ------------------------------------------------------- |
    | Host Region | The Region of your Trend Micro Vision One XDR Console.  |
    | API Key     | The API Key of your Trend Micro Vision One XDR Console. |

2. Click the Save button to save your settings.

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
[3]: https://docs.datadoghq.com/logs/explorer/
[4]: https://www.datadoghq.com/product/cloud-siem/
[5]: https://success.trendmicro.com/en-US/solution/ka-0015959
