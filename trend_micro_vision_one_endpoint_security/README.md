## Overview

[Trend Micro Vision One Endpoint Security][1] is a cloud-based solution specifically designed for endpoints, servers, and cloud workloads.

This integration ingests the following logs:

- Application Control: Application Control logs provides information about application control violations on your network, such as the violated Security Agent policy and criteria
- Attack Discovery: Attack discovery logs provides information about threats detected by Attack Discovery
- Behavior Monitoring: Behavior monitoring logs provide information about Behavior Monitoring events on your network
- C&C Callback: C&C callback logs provides information about C&C callback events detected on your network
- Content Violation: Content violation logs provides information about the email messages with content violations, such as the managed product that detected the content violation, the sender(s) and recipients(s) of the email message, the name of the content violation policy, and the total number of violations detected
- Data Loss Prevention: Data loss prevention logs provides information about incidents detected by Data Loss Prevention
- Device Control: Device control logs provides information about Device Access Control events on your network
- Intrusion Prevention: Intrusion prevention logs provides information to help you achieve timely protection against known and zero-day attacks, defend against web application vulnerabilities, and identify malicious software accessing the network
- Network Content Inspection: Network content inspection logs provides information about network content violations on your network
- Predictive Machine Learning: Predictive machine learning logs provides information about advanced unknown threats detected by Predictive Machine Learning
- Spyware/Grayware: Spyware/Grayware logs provides information about the spyware/grayware detections on your network, such as the managed product that detected the spyware/grayware, the name of the spyware/grayware, and the name of the infected endpoint
- Suspicious File Information: Suspicious file information logs provides information about suspicious files detected on your network
- Virtual Analyzer Detections: Virtual analyzer logs provides information about advanced unknown threats detected by Virtual Analyzer
- Virus/Malware: Virus/Malware logs provides information about the virus/malware detections on your network, such as the managed product that detected the viruses/malware, the name of the virus/malware, and the infected endpoint
- Web Violation: Web violation logs provides information about web violations on your network

Use out-of-the-box dashboards to gain detailed insights into system events, network events, and data loss prevention events, security detection and observation, and compliance monitoring.

## Setup

### Generate API credentials in Trend Micro Vision One Endpoint Security

1. Log in to the Trend Micro Vision One console.
2. Go to **Endpoint Security** (Sidebar) > **Standard Endpoint Protection** > **Administration** > **Settings** > **Automation API Access Settings**.
3. Click **Add**.<br> The Application Access Settings section appears and displays the following information:
   1. **API URL**: The API Host of the Trend Micro Vision One Endpoint Security console.
   2. **Application ID**: The Application ID of the Trend Micro Vision One Endpoint Security console.
   3. **API key**: The API key of the Trend Micro Vision One Endpoint Security console.
4. Tick the **Enable application integration using Apex Central Automation APIs** checkbox.
5. Configure the following settings.
   1. **Application name**: Specify an easily identifiable name for the application.
   2. **Communication time-out**: Select 120 seconds for a request to reach Apex Central after the application generates the request.
6. Click **Save**.

### Get Timezone of Trend Micro Vision One console

1. Log in to the Trend Micro Vision One console.
2. Go to **Administration** (Sidebar) > **Console Settings** > **Time Zone**.
3. Check the **Timezone** from **Current console time**.

### Connect your Trend Micro Vision One Endpoint Security Account to Datadog

1. Add your API host, application ID, API key and select the time zone from the dropdown.
   | Parameters     | Description                                                             |
   | -------------- | ----------------------------------------------------------------------- |
   | API Host       | The API host of Trend Micro Vision One Endpoint Security console.       |
   | Application ID | The application ID of Trend Micro Vision One Endpoint Security console. |
   | API Key        | The API key of of Trend Micro Vision One Endpoint Security console.     |
   | Time Zone      | The time zone of the Trend Micro Vision One console.                    |

2. Click the **Save** button to save your settings.

## Data Collected

### Logs

The Trend Micro Vision One Endpoint Security integration collects and forwards security events, including system events, network events, and data loss prevention events to Datadog.

### Metrics

The Trend Micro Vision One Endpoint Security integration does not include any metrics.

### Events

The Trend Micro Vision One Endpoint Security integration does not include any events.

## Support

For additional assistance, contact [Datadog support][2].

[1]: https://www.trendmicro.com/en_in/business/products/endpoint-security.html
[2]: https://docs.datadoghq.com/help/
