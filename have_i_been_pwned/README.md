# Have I Been Pwned

## Overview

[Have I Been Pwned][1] provides a personalized view of compromised data based on your email address, domain and other information you've added.

This integration ingests the following logs:

- Breach Logs: The breach refers to a security incident where data from a system has been exposed to unauthorized parties.

This integration collects breach logs and send them to Datadog for analysis. The logs are parsed and enriched using Datadog's built-in pipeline, which allows for searching and analysis. Dashboards and Cloud SIEM detection rules are included to help monitor message logs and improve security.

## Setup

### Get an API key from the Have I Been Pwned Portal

1. Login to the [Have I Been Pwned][2] dashboard.
2. Navigate to **API Key**.
3. Click **Generate New API Key**.
4. Save generated **API Key**.


### Connect your Have I Been Pwned Account to Datadog

1. Add your Have I Been Pwned credentials.

    | Parameters                            | Description                                                  |
    | ------------------------------------- | ------------------------------------------------------------ |
    | API key                               | The API key for your Have I Been Pwned account               |

2. Click the **Save** button to save your settings.

## Data Collected

### Logs

The Have I Been Pwned integration collects and forwards message logs to Datadog.

### Metrics

The Have I Been Pwned integration does not include any metrics.

### Events

The Have I Been Pwned integration does not include any events.

## Support

Need help? Contact [Datadog support][3].

[1]: https://haveibeenpwned.com/
[2]: https://haveibeenpwned.com/Dashboard
[3]: https://docs.datadoghq.com/help/