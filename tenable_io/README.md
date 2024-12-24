# Tenable.io

## Overview

[Tenable.io][1] is the cloud platform that provides a rich capability for discovery, assessment, reporting, and prioritization of vulnerabilities across systems and services. It enhances visibility with asset discovery and helps organizations manage their security posture effectively.

The Tenable.io integration collects the following types of logs:

- **Activity**: This endpoint contains information of user actions, system events, scans, and security control tasks, such as managing permissions, assigning roles, and handling security events.
- **Vulnerability**: This endpoint contains information of vulnerabilities and the associated vulnerable assets.

This integration collects logs from the sources listed above and sends them to Datadog.

## Setup

### Generate API credentials in Tenable.io

1. Log into your [Tenable.io][4] account.
2. Click profile icon and select **My Profile**.
3. Go to the **API Keys** option in the navigation.
4. Click **Generate** button in the bottom right corner.
5. Review the message in the warning dialog box and click **Continue**.
6. The **access Key** and **secret Key** will be generated.

### Connect your Tenable.io account to Datadog

1. Add your access key and secret key
    |Parameters|Description|
    |--------------------|--------------------|
    |Access Key|The access key of Tenable.io account.|
    |Secret Key|The secret key of Tenable.io account.|
2. Click the **Save** button to save your settings.

## Data Collected

### Logs 

The Tenable.io integration collects logs and forwards them to Datadog.

### Metrics

The Tenable.io integration does not include any metrics.

### Events

The Tenable.io integration does not include any events.

## Support

Need help? Contact [Datadog support][5].

[1]: https://www.tenable.com/
[2]: https://docs.datadoghq.com/logs/explorer/
[3]: https://www.datadoghq.com/product/cloud-siem/
[4]: https://cloud.tenable.com/tio/app.html#/login
[5]: https://docs.datadoghq.com/help/