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
=======
# Agent Check: Have I Been Pwned

## Overview

This check monitors [Have I Been Pwned][1].

## Setup

### Installation

The Have I Been Pwned check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

!!! Add list of steps to set up this integration !!!

### Validation

!!! Add steps to validate integration is functioning as expected !!!

## Data Collected

### Metrics

Have I Been Pwned does not include any metrics.

### Events

Have I Been Pwned does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/help/
