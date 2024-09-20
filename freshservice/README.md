# Freshservice Integration For Datadog

## Overview

[Freshservice][1] is a cloud-based IT service management (ITSM) solution that streamlines ticketing, asset management, and service desk operations. It offers robust features for problem resolution, change control, and IT asset tracking. With a user-friendly interface and automation capabilities, Freshservice empowers organizations to enhance IT support efficiency, improve service delivery, and ensure seamless IT operations.

This integration ingests the following logs:

- Tickets: Case sheet that contains the history of an issue, from the time it was reported to the time it is closed

The Freshservice integration seamlessly collect ticket logs of Freshservice channeling them into Datadog for analysis. Leveraging the built-in logs pipeline, these logs are parsed and enriched, enabling effortless search and analysis. The integration provides insight into ticket logs through the out-of-the-box dashboards.

## Setup

### Configuration

#### Freshservice Configuration

Steps to get API Key

1. Login to [Freshservice][2] platform with your credentials.
2. Click on your profile picture on the top right corner of your portal.
3. Go to Profile settings Page.
4. API key will be displayed on the right side section of the page.

#### Freshservice Integration Configuration

Configure the Datadog endpoint to forward Freshservice events as logs to Datadog.

1. Navigate to Freshservice.
2. Add your Freshservice API Key.

| Freshservice Parameters | Description                                                                |
| ----------------------- | -------------------------------------------------------------------------- |
| Domain Name             | The Domain Name from Freshservice portal URL                               |
| API Key                 | The Personal API key of Freshservice  to authenticate the request          |

## Data Collected

### Logs

The integration collects and forwards Freshservice Tickets logs to Datadog.

### Metrics

The Freshservice integration does not include any metrics.

### Events

The Freshservice integration does not include any events.

## Support

For further assistance, contact [Datadog Support][3].

[1]: https://developers.freshservice.com/
[2]: https://login.freshworks.com/email-login/
[3]: https://docs.datadoghq.com/help/