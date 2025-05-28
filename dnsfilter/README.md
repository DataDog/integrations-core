# DNSFilter

## Overview

[DNSFilter][1] is a cloud-based content filtering and threat protection by blocking internet threats at the DNS layer. It protects organizations by preventing access to malicious domains, phishing sites, and other cyber threats, ensuring a safer internet experience.

This integration ingests the following logs:

- DNS Traffic Logs: Represents information about allowed and blocked DNS requests, threats, domains accessed, policies, networks, and other DNS-related traffic data.

This integration seamlessly collects DNS Traffic Logs, channeling them into Datadog for analysis. Leveraging the built-in logs pipeline, these logs are parsed and enriched, enabling effortless search and analysis. The integration provides insight into dns traffic logs through out-of-the-box dashboards and includes ready-to-use Cloud SIEM detection rules for improved monitoring and security.

## Setup

### Generate API Credentials in DNSFilter

1. Login to the **DNSFilter dashboard** and navigate to **Account**.
2. Select **Account Settings**.
3. Navigate to **Security** tab.
4. Navigate to **API Keys** section, then click **CREATE KEY**.
5. Enter a key **Name** and select an **Expiration**.
6. Click **GENERATE KEY**.
7. Fetch API Key from **Your API Key** Section.

### Connect your DNSFilter Account to Datadog

1. Add your API Key.

    | Parameters                            | Description                                                  |
    | ------------------------------------- | ------------------------------------------------------------ |
    | API Key                               | The API Key of your DNSFilter Platform                       |
    
2. Click the **Save** button to save your settings.

## Data Collected

### Logs

The DNSFilter integration collects and forwards dns traffic logs to Datadog.

### Metrics

The DNSFilter integration does not include any metrics.

### Events

The DNSFilter integration does not include any events.

## Support

Need help? Contact [Datadog support][2].

[1]: https://www.dnsfilter.com/
[2]: https://docs.datadoghq.com/help/
