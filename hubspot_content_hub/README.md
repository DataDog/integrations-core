# HubSpot Content Hub

## Overview

[HubSpot Content Hub][1] is an all-in-one content marketing software that helps marketers create and manage content at scale. It helps create rich, expertise-backed content across various formats and channels.

The HubSpot Content Hub integration collects Activity Logs (audit, login, security) and Analytics Metrics (breakdown categories, content types), sending them to Datadog for detailed analysis. The logs are parsed and enriched for efficient searching, while the metrics provide insights into content performance.

Use Datadog [Reference Tables][2] to enrich your telemetry with metadata from HubSpot. You can map value fields to a primary key to automatically append these fields to logs or events containing that key.

The integration includes dashboards that show and analyze both Activity Logs and Analytics Metrics, making it easier to monitor and understand trends and issues.

## Setup

To integrate HubSpot with Datadog, you must authenticate as an owner of the HubSpot organization that Datadog fetches data from.

### Metrics and Logs

To collect HubSpot metrics and logs, click the  **Authorize** button to authenticate using OAuth.

### Companies Reference Tables

Import company data from HubSpot as a Reference Table to enrich your Datadog logs and metrics with CRM details. You can also join Reference Tables with Product Analytics to correlate activity data across accounts.

#### Get Started

- Enable **Companies Reference Table** and click the **Authorize** button.

#### After Setup

- Datadog automatically creates one Companies Reference Table for each account, using the format `hubspot_companies_hubspotaccountid`.
- Your [HubSpot Reference Tables][3] are available after a few minutes. Datadog automatically starts syncing data after the table is created.
- Use [Event Management][4] to monitor your Reference Table's creation. You'll see progress events, success confirmations, and any errors that occur.
- When ingestion succeeds, a [success event][5] appears for your Reference Table.

#### For Existing Accounts

- To create a Company Reference Table for an existing HubSpot account, edit the account and select the Companies Reference Table toggle.

## Data Collected

### Logs

The HubSpot Content Hub integration collects and forwards Activity logs to Datadog.

### Metrics

The HubSpot Content Hub integration collects and forwards Analytics metrics to Datadog.

{{< get-metrics-from-git "hubspot-content-hub" >}}

### Service Checks

The HubSpot Content Hub integration does not include any service checks.

### Events

The HubSpot Content Hub integration does not include any events.

### Reference Tables

[Reference Tables][2] allow you to automatically enrich and join your telemetry with additional fields from Companies defined in your HubSpot account.

## Troubleshooting

Need help? Contact [Datadog support][6].

[1]: https://www.hubspot.com/products/content
[2]: /reference-tables
[3]: /reference-tables?order=desc&p=1&sort=updated_at&source=HUBSPOT_CONTENT_HUB
[4]: /event/explorer?query=source%3Ahubspot_content_hub&from_ts=1767286800000&to_ts=1767294000000&live=true
[5]: /event/explorer?query=source%3Ahubspot_content_hub%20status%3Aok&from_ts=1767286800000&to_ts=1767294000000&live=true
[6]: https://app.hubspot.com/login
