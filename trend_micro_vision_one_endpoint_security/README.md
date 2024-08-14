## Overview

[Trend Micro Vision One Endpoint Security][1] is a cloud-based solution specifically designed for endpoints, servers and cloud workloads.

This integration ingests the following logs:

- Application Control
- Attack Discovery
- Behavior Monitoring
- C&C Callback
- Content Violation
- Data Loss Prevention
- Device Control
- Intrusion Prevention
- Network Content Inspection
- Predictive Machine Learning
- Spyware/Grayware
- Suspicious File Information
- Virtual Analyzer Detections
- Virus/Malware
- Web Violation

Use out-of-the-box dashboards to visualize detailed insights into system events, network events and data loss prevention events, security detection and observation, and compliance monitoring.

## Setup

### Configuration

#### Get Credentials of Trend Micro Vision One Endpoint Security

1. Log in to the Trend Micro Vision One console.
2. Go to **Endpoint Security** -> **Standard Endpoint Protection**.
3. Then, Go to **Administration** -> **Settings** -> **Automation API Access Settings**.<br> The Automation API Access Settings screen appears.
4. Click **Add**.<br> The Application Access Settings section appears and displays the following information:
   1. **API URL**: The Host of the Trend Micro Vision One Endpoint Security console
   2. **Application ID**: The Application ID of the Trend Micro Vision One Endpoint Security console
   3. **API key**: The API key of the Trend Micro Vision One Endpoint Security console
5. Copy and store the API host, Application ID, and App key in a secure location.
6. Select **Enable application integration using Apex Central Automation APIs**.
7. Configure the following settings.
   1. **Application name**: Specify an easily identifiable name for the application.
   2. **Communication time-out**: Select 120 seconds for a request to reach Apex Central after the application generates the request.
8. Click **Save**.<br> The Automation API Access Settings screen appears and displays the newly added application in the table.

#### Get Timezone of Trend Micro Vision One console

1. Go to **Administration** > **Console Settings**.
2. Check the timezone from **Current console time**.
3. Ensure this timezone is selected in the integration configuration.

#### Configure the Trend Micro Vision One Endpoint Security and Datadog Integration

Configure the Datadog endpoint to forward Trend Micro Vision One Endpoint Security logs to Datadog.

1. Navigate to `Trend Micro Vision One Endpoint Security`.
2. Add your Trend Micro Vision One Endpoint Security credentials.

| Trend Micro Vision One Endpoint Security Parameters | Description                                                             |
| --------------------------------------------------- | ----------------------------------------------------------------------- |
| API Host                                            | The API Host of Trend Micro Vision One Endpoint Security console.       |
| Application ID                                      | The Application ID of Trend Micro Vision One Endpoint Security console. |
| API Key                                             | The API Key of of Trend Micro Vision One Endpoint Security console.     |
| Time Zone                                           | The Time Zone of the Trend Micro Vision One console.                    |

## Data Collected

### Logs

The Trend Micro Vision One Endpoint Security integration collects and forwards security events, including system events, network events and data loss prevention events to Datadog.

### Metrics

The Trend Micro Vision One Endpoint Security integration does not include any metrics.

### Events

The Trend Micro Vision One Endpoint Security integration does not include any events.

## Support

For any further assistance, contact [Datadog support][2].

[1]: https://www.trendmicro.com/en_in/business/products/endpoint-security.html
[2]: https://docs.datadoghq.com/help/
