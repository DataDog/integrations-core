# Tenable.io

## Overview

[Tenable.io][1] is the cloud platform that provides a rich capability for discovery, assessment, reporting, and prioritization of vulnerabilities across systems and services. It enhances visibility with asset discovery and helps organizations manage their security posture effectively.

The Tenable.io integration collects the following types of logs:

- **Activity**: This endpoint contains information of user actions, system events, scans, and security control tasks, such as managing permissions, assigning roles, and handling security events.
- **Vulnerability**: This endpoint contains information on vulnerabilities and the associated vulnerable assets.

This integration collects logs from the sources listed above and sends them to Datadog.

**Minimum Agent version:** 7.59.1

## Setup

### Generate API credentials in Tenable.io

1. Log in to [Tenable.io][4] with an account that has the `Administrator` user role.
2. Click the profile icon and select **My Profile**.
3. Navigate to the **API Keys** section.
4. Click the **Generate** button in the lower right-corner of the page.
5. Review the message in the warning dialog box and click **Continue** to generate the **access Key** and **secret Key**.

### Connect your Tenable.io account to Datadog

1. Add your access key and secret key
    |Parameters|Description|
    |--------------------|--------------------|
    |Access Key|The access key for your Tenable.io account.|
    |Secret Key|The secret key for your Tenable.io account.|
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