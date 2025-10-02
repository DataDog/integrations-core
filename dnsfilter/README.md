# DNSFilter

## Overview

[DNSFilter][1] is a cloud-based content filtering tool that blocks internet threats at the DNS layer. It helps protect organizations by preventing access to malicious domains, phishing sites, and other cyber threats, ensuring a safer and more secure internet experience.

This integration ingests the following logs:

- DNS Traffic Logs: Represents information about allowed and blocked DNS requests, threats, domains accessed, policies, networks, and other DNS-related traffic data.

This integration collects DNS Traffic Logs, channeling them into Datadog for analysis. Leveraging the built-in logs pipeline, these logs are parsed and enriched, enabling search and analysis. The integration provides insight into DNS traffic logs through out-of-the-box dashboards and includes ready-to-use Cloud SIEM detection rules for improved monitoring and security.

**Minimum Agent version:** 7.66.0

## Setup

### Generate API credentials in DNSFilter

1. Login to the **DNSFilter dashboard** and navigate to **Account**.
2. Select **Account Settings**.
3. Navigate to the **Security** tab.
4. Navigate to the **API Keys** section, then click **CREATE KEY**.
5. Enter a key **Name** and select an **Expiration**.
6. Click **GENERATE KEY**.
7. Fetch the API Key from the **Your API Key** Section.

### Connect your DNSFilter account to Datadog

1. Add your API Key.

    | Parameters                            | Description                                                  |
    | ------------------------------------- | ------------------------------------------------------------ |
    | API Key                               | The API Key of your DNSFilter platform                       |
    
2. Click the **Save** button to save your settings.

## Data Collected

### Logs

The DNSFilter integration collects and forwards DNS traffic logs to Datadog.

### Metrics

The DNSFilter integration does not include any metrics.

### Events

The DNSFilter integration does not include any events.

## Support

Need help? Contact [Datadog support][2].

[1]: https://www.dnsfilter.com/
[2]: https://docs.datadoghq.com/help/