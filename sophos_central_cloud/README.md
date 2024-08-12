# Sophos Central Cloud Integration for Datadog

## Overview

[Sophos Central][1] is a unified cloud-based management platform provided by Sophos, a company specializing in digital security. It allows users to manage various Sophos security products from a single interface. It's designed to simplify security management for businesses of all sizes by consolidating multiple security products into a single, cloud-based platform.

This integration ingests the following logs:

- Alerts
- Events

The Sophos Central Cloud integration seamlessly collects all the above listed logs, channeling them into Datadog for analysis. Leveraging the built-in logs pipeline, these logs are parsed and enriched, enabling effortless search and analysis. The integration provides insight into alerts and events through the out-of-the-box dashboards. Additionally, the integration enriches corresponding endpoint details along with alert and event logs through the **get_endpoint_details** flag.

## Setup

### Configuration

#### Sophos Central Cloud Configuration

1. Login to [**Sophos Central Platform**][2] with your credentials.
2. From Sophos Central Admin, go to **My Products** > **General Settings** > **API Credentials Management**.
3. Click **Add Credential**.
4. Provide a credential name, select the appropriate role, add an optional description, and click the **Add** button. The **API credential Summary** for this credential is displayed.
5. Click **Show Client Secret** to display the **Client Secret**.
6. Copy the **Client ID** and **Client Secret**.

#### Sophos Central Cloud DataDog Integration Configuration

Configure the Datadog endpoint to forward Sophos Central Cloud events as logs to Datadog.

1. Navigate to `Sophos Central Cloud`.
2. Add your Sophos Central Cloud credentials.

| Sophos Central Cloud Parameters | Description                                                                |
| ------------------------------- | -------------------------------------------------------------------------- |
| Client ID                       | The Client ID from Sophos Central Cloud.                                         |
| Client Secret                   | The Client Secret from Sophos Central Cloud.                                     |
| Get Endpoint Details            | Set to "true" to collect endpoint details for Sophos Central Cloud Alert and Event Logs, otherwise set to "false". Default is "true"                 |

## Data Collected

### Logs

The integration collects and forwards Sophos Central Cloud Alert and Event logs to Datadog.

### Metrics

The Sophos Central Cloud integration does not include any metrics.

### Events

The Sophos Central Cloud integration does not include any events.

## Support

For further assistance, contact [Datadog Support][3].

[1]: https://www.sophos.com/en-us/products/sophos-central
[2]: https://cloud.sophos.com/manage/login
[3]: https://docs.datadoghq.com/help/