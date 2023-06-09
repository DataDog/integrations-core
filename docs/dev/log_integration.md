---
title: Create a Log Integration
kind: documentation
aliases:
- /logs/faq/partner_log_integration
further_reading:
- link: "/integrations/#cat-log-collection"
  tag: "Documentation"
  text: "See existing Datadog Log integrations"
- link: "/logs/explorer/facets/"
  tag: "Documentation"
  text: "Learn about log facets"
- link: "/logs/explorer/"
  tag: "Documentation"
  text: "Learn about the Log Explorer"
- link: "/logs/log_configuration/pipelines/"
  tag: "Documentation"
  text: "Learn about log pipelines"
---

## Overview

This page walks Technology Partners through creating a Datadog Log integration.

## Log integrations

Use the [Logs Ingestion HTTP endpoint][1] to send logs to Datadog. 

## Development process

### Guidelines

When creating a log integration, consider the following best practices:

Set the `source` tag to the integration name.
: Datadog recommends that the `source` tag is set to `<integration_name>` and that the `service` tag is set to the name of the service that produces the telemetry. For example, the `service` tag can be used to differentiate logs by product line. </br></br> For cases where there aren't different services, set `service` to the same value as `source`. The `source` and `service` tags must be non-editable by the user because the tags are used to enable integration pipelines and dashboards. The tags can be set in the payload or through the query parameter, for example, `?ddsource=example&service=example`. </br></br> The `source` and `service` tags must be in lowercase. 

The integration must support all Datadog sites.
: The user must be able to choose between the different Datadog sites whenever applicable. See [Getting Started with Datadog Sites][2] for more information about site differences. </br></br> Your Datadog site endpoint is `http-intake.logs`.{{< region-param key="dd_site" code="true" >}}.

Allow users to attach custom tags while setting up the integration.
: Datadog recommends that manual user tags are sent as key-value attributes in the JSON body. If it's not possible to add manual tags to the logs, you can send the tags using the `ddtags=<TAGS>` query parameter. See the [Send Logs API documentation][1] for examples.

Send data without arrays in the JSON body whenever possible. 
: While it's possible to send some data as tags, Datadog recommends sending data in the JSON body and avoiding arrays. This allows you more flexibility with the operations you can carry out on the data in Datadog Log Management. 

Do not log Datadog API keys.
: Datadog API keys can either be passed in the header or as part of the HTTP path. See [Send Logs API documentation][1] for examples. Datadog recommends using methods that do not log the API key in your setup.

Do not use Datadog application keys.
: The Datadog application key is different from the API key and is not required to send logs using the HTTP endpoint. 

## Set up the log integration assets in your Datadog partner account 

### Configure the log pipeline

Logs sent to Datadog are processed in [log pipelines][13] to standardize them for easier search and analysis.

To set up a log pipeline:

1. Navigate to [**Logs** > **Pipelines**][3].
2. Click **+ New Pipeline**.
3. In the **Filter** field, enter a unique `source` tag that defines the log source for the Technology Partner's logs. For example, `source:okta` for the Okta integration. **Note**: Make sure that logs sent through the integration are tagged with the correct source tags before they are sent to Datadog.
4. Optionally, add tags and a description.
5. Click **Create**.

You can add processors within your pipelines to restructure your data and generate attributes. For example:

- Use the [date remapper][4] to define the official timestamp for logs.
- Use the attribute [remapper][5] to remap attribute keys to standard [Datadog attributes][6]. For example, an attribute key that contains the client IP must be remapped to `network.client.ip` so Datadog can display Technology Partner logs in out-of-the-box dashboards.
- Use the [service remapper][7] to remap the `service` attribute or set it to the same value as the `source` attribute.
- Use the [grok processor][8] to extract values in the logs for better searching and analytics. 
- Use the [message remapper][9] to define the official message of the log and make certain attributes searchable by full text.

For a list of all log processors, see [Processors][10].

### Set up facets in the Log Explorer

You can optionally create [facets][12], which appear in out-of-the-box dashboard widgets, in the [Log Explorer][16].

- A [facet][14] is used to get relative insights and to count unique values.
- A [measure][15] is a type of facet used for searches over a range. For example, adding a measure for latency duration allows users to search for all logs above a certain latency. **Note**: Define the [unit][11] of a measure facet based on what the attribute represents.

To add a facet or measure:

1. Click on a log that contains the attribute you want to add a facet or measure for. 
2. In the log panel, click the Cog icon next to the attribute.
3. Select **Create facet/measure for @attribute**.
4. For a measure, to define the unit, click **Advanced options**. Select the unit based on what the attribute represents.
4. Click **Add**.

To easily navigate the facet list, group similar facets together. For fields specific to the integration logs, create a group with the same name as the `source` tag. 

1. In the log panel, click the Cog icon next to the attribute that you want in the new group.
2. Select **Edit facet/measure for @attribute**. If there isn't a facet for the attribute yet, select **Create facet/measure for @attribute**.
3. Click **Advanced options**.
4. In the **Group** field, enter the name of the new group, and select **New group**.
5. Click **Update**.

See the [default standard attribute list][6] for the standard Datadog attributes under their specific groups. 

## Review and deploy the integration

Datadog reviews the log integration and provides feedback to the Technology Partner. In turn, the Technology Partner reviews and makes changes accordingly. This review process is done over email.

Once reviews are complete, Datadog creates and deploys the new log integration assets.

## Further reading

{{< partial name="whats-next/whats-next.html" >}}

[1]: https://docs.datadoghq.com/api/latest/logs/#send-logs
[2]: https://docs.datadoghq.com/getting_started/site/
[3]: https://app.datadoghq.com/logs/pipelines
[4]: https://docs.datadoghq.com/logs/log_configuration/processors/?tab=ui#log-date-remapper
[5]: https://docs.datadoghq.com/logs/log_configuration/processors/?tab=ui#remapper
[6]: https://docs.datadoghq.com/logs/log_configuration/attributes_naming_convention/#default-standard-attribute-list
[7]: https://docs.datadoghq.com/logs/log_configuration/processors/?tab=ui#service-remapper
[8]: https://docs.datadoghq.com/logs/log_configuration/processors/?tab=ui#grok-parser
[9]: https://docs.datadoghq.com/logs/log_configuration/processors/?tab=ui#log-message-remapper
[10]: https://docs.datadoghq.com/logs/log_configuration/processors/
[11]: https://docs.datadoghq.com/logs/explorer/facets/#units
[12]: https://docs.datadoghq.com/logs/explorer/facets/
[13]: https://docs.datadoghq.com/logs/log_configuration/pipelines/
[14]: https://docs.datadoghq.com/glossary/#facet
[15]: https://docs.datadoghq.com/glossary/#measure
[16]: https://docs.datadoghq.com/logs/explorer/