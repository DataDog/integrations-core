---
title: Integration Assets Reference
kind: documentation
---

## Configuration file

When preparing a new integration, you must include an example configuration that contains the necessary options and reasonable defaults. The example configuration file, which in this case is located at `<CHECK_NAME>/datadog_checks/<CHECK_NAME>/data/conf.yaml.example`, has two top-level elements: `init_config` and `instances`. The configuration under `init_config` is applied to the integration globally, and is used in every instantiation of the integration, whereas anything within `instances` is specific to a given instantiation.

Configuration blocks in either section take the following form:

```yaml
## @<COMMAND> [- <ARGS>]
## <DESCRIPTION LINE 1>
## <DESCRIPTION LINE 2>
#
<KEY>: <VALUE>
```

Configuration blocks follow a few guidelines:

- Description must not be empty
- Placeholders should always follow this format: `<THIS_IS_A_PLACEHOLDER>`, as per the documentation [contributing guidelines][1]:
- All required parameters are **not** commented by default.
- All optional parameters are commented by default.
- If a placeholder has a default value for an integration (like the status endpoint of an integration), it can be used instead of a generic placeholder.

### `@param` specification

Practically speaking, the only command is `@param`, which is used to describe configuration blocks—primarily for documentation purposes. `@param` is implemented using one of the following forms:

```text
@param <name> - <type> - required
@param <name> - <type> - optional
@param <name> - <type> - optional - default: <defval>
```

Arguments:

- `name`: the name of the parameter, such as `search_string` (mandatory).
- `type`: the data type for the parameter value (mandatory). Possible values:
  - _boolean_
  - _string_
  - _integer_
  - _double_
  - _float_
  - _dictionary_
  - _list\*_
  - _object_
- `defval`: default value for the parameter; can be empty (optional).

`list` and `object` variables span over multiple lines and have special rules.

- In a `list`, individual elements are not documented with the `@param` specification
- In an `object` you can choose to either document elements individually with the `@param` specification or to have a common top-level description following the specification of the object itself.

### Optional parameters

An optional parameter must be commented by default. Before every line the parameter spans on, add `#` with the same indentation as the `@param` specification.

### Block comments

You can add a block comment anywhere in the configuration file with the following rules:

- Comments start with `##`
- Comments should be indented like any variable (the hyphen doesn't count)

For more information about YAML syntax, see [Wikipedia][2]. Feel free to play around with the [Online YAML Parser][3], too!

## Manifest file

Every integration contains a `manifest.json` file that describes operating parameters, positioning within the greater Datadog integration eco-system, and other such items.

There are two versions of the `manifest.json` file. While we will continue supporting manifest version 1 for existing integrations, all **new** integrations, Datadog Apps, and Marketplace offerings should use version 2 of the manifest.

If you see the following at the top of your `manifest.json` file, this means you are using version 2:

```"manifest_version": "2.0.0"```

Otherwise, you can assume that you are using version 1. 

These two versions have different attributes and structures. You can find the complete list of mandatory and optional attributes for both versions of the `manifest.json` file below: 

{{< tabs >}}
{{% tab "Manifest Version 2" %}}

| Attribute                                            | Type                        | Mandatory/Optional                        | Description                                                                                                                                                                                                                                 |
|------------------------------------------------------|-----------------------------|-------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `manifest_version`                                   | String Enum                 | Mandatory                                 | Version of the manifest schema. Supported values include `1.0.0` and `2.0.0`.                                                                                                                                                               |
| `app_id`                                             | String                      | Mandatory                                 | The unique identifying name of this offering. Usually kebab case of the app title. For example, if the app title is "Marketplace Offering", then the `app_id` would be `marketplace-offering`.                                              |
| `app_uuid`                                           | UUID                        | Mandatory                                 | Globally unique UUID for this application.                                                                                                                                                                                                  |
| `assets`                                             | Dictionary                  | Mandatory                                 | Object containing any Datadog installable entity.                                                                                                                                                                                           |
| `assets[dashboards]`                                 | Dictionary                  | Optional                                  | Out-of-the-box dashboards associated with this offering.                                                                                                                                                                                    |
| `assets[dashboards["dashboard_short_name"]]`         | String                      | Mandatory                                 | Key/value pairs of any out-of-the-box dashboards. The key is the globally unique short name of the dashboard and the value is the relative path to the dashboard's JSON definition in relation to this manifest.                            |
| `assets[integration]`                                | Dictionary                  | Optional                                  | Object containing information about the integration.                                                                                                                                                                                        |
| `assets[integration[configuration]]`                 | Dictionary                  | Mandatory, can be `{ }`                   | Object representing the configuration specification for this integration.                                                                                                                                                                   |
| `assets[integration[configuration[spec]]]`           | String                      | Mandatory                                 | Relative path to where the configuration spec lives in relation to this manifest.                                                                                                                                                           |
| `assets[integration[events]]`                        | Dictionary                  | Mandatory                                 | Information about events emitted by this integration.                                                                                                                                                                                       |
| `assets[integration[events[creates_events]]]`        | Boolean                     | Mandatory                                 | Whether or not this integration emits events to Datadog.                                                                                                                                                                                    |
| `assets[integration[metrics]]`                       | Dictionary                  | Mandatory                                 | Information about the metrics this integration emits.                                                                                                                                                                                       |
| `assets[integration[metrics[check]]]`                | String or List of String    | Mandatory                                 | A string or list representing metrics that this integration always emits on every run.                                                                                                                                                     |
| `assets[integration[metrics[metadata_path]]]`        | String                      | Mandatory                                 | Relative path to where the metrics metadata lives in relation to this manifest.                                                                                                                                                             |
| `assets[integration[metrics[prefix]]]`               | String                      | Mandatory                                 | The prefix for metrics emitted by this integration.                                                                                                                                                                                         |
| `assets[integration[service_checks]]`                | Dictionary                  | Mandatory, but can be `{ }`               | Information about service checks emitted by this integration.                                                                                                                                                                               |
| `assets[integration[service_checks[metadata_path]]]` | String                      | Mandatory                                 | Relative path to where the service check metadata lives in relation to this manifest.                                                                                                                                                       |
| `assets[integration[source_type_name]]`              | String                      | Mandatory                                 | User-facing name of this integration.                                                                                                                                                                                                       |
| `assets[monitors]`                                   | Dictionary                  | Optional                                  | Recommended monitors.                                                                                                                                                                                                                       |
| `assets[monitors["monitor_short_name"]]`             | String                      | Mandatory                                 | Key/value pairs for any recommended monitors. The key is the globally unique short name of the monitor and the value is the relative path to the monitor's JSON definition in relation to this manifest.                                   |
| `author `                                            | Dictionary                  | Mandatory                                 | Information about the author of this app.                                                                                                                                                                                                   |
| `author[homepage] `                                  | String (URL)                | Mandatory                                 | The web URL to the homepage of the author.                                                                                                                                                                                                  |
| `author[name]`                                       | String                      | Mandatory                                 | The human-readable name for this company.                                                                                                                                                                                                   |
| `author[sales_email]`                                | String (Email)              | Mandatory                                 | The email to contact for any subscription-level events.                                                                                                                                                                                     |
| `author[support_email]`                              | String (Email)              | Mandatory                                 | The email to contact for any support and maintenance queries.                                                                                                                                                                               |
| `author[vendor_id]`                                  | String                      | Mandatory                                 | The vendor ID to use for subscription purposes. Must be globally unique and cannot be changed. Should follow the strict standards of `app_id` where only dashes and alphabetic chars are allowed. This value is provided to partners.       |
| `display_on_public_website `                         | Boolean                     | Mandatory                                 | Whether or not information about this listing is displayed on the public Datadog docs site. Once this is set to True, it cannot be changed.                                                                                                 |
| `legal_terms `                                       | Dictionary                  | Mandatory                                 | Any legal documentation that a user needs to agree to in order to use this app.                                                                                                                                                             |
| `legal_terms[eula] `                                 | String                      | Mandatory                                 | Relative path to the EULA (End User License Agreement) PDF in relation to this manifest.                                                                                                                                                    |
| `pricing`                                            | Array of Dictionaries       | Mandatory                                 | List of objects representing the pricing model of the integration. See [Marketplace GitHub repository][1] for pricing details. The Marketplace GitHub repository is private, email marketplace@datadog.com for access.                      |
| `tile`                                               | Dictionary                  | Mandatory                                 | Information about this offering                                                                                                                                                                                                             |
| `tile[media]`                                        | Array of Dictionaries       | Mandatory, can be `[ ]`                   | Information about various image and video style objects that are presented in the media gallery carousel on the listing page.                                                                                                               |
| `tile[media[media_type]]`                            | String or Enum              | Mandatory                                 | The type of media this is. Allowed values are `image` and `video`.                                                                                                                                                                          |
| `tile[media[caption]]`                               | String                      | Mandatory                                 | The caption for the image.                                                                                                                                                                                                                  |
| `tile[media[image_url]]`                             | String                      | Mandatory                                 | The relative path to this image in relation to this manifest file.                                                                                                                                                                          |
| `tile[classifier_tags]`                              | Array of String             | Mandatory, can be `[ ]`                   | Some classifier information about this app. This includes information such as `supported_os` and `available_offerings`.                                                                                                                     |
| `tile[description]`                                  | String\[80\]                | Mandatory                                 | A brief description of what this offering provides. Limited to 80 characters.                                                                                                                                                               |
| `tile[title]`                                        | String\[50\]                | Mandatory                                 | The user-friendly title for this app.                                                                                                                                                                                                       |


[1]: https://github.com/DataDog/marketplace#faq


{{% /tab %}}

{{% tab "Manifest Version 1" %}}


| Attribute                   | Type            | Mandatory/Optional | Description                                                                                                                                                                                                              |
| --------------------------- | --------------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `integration_id`            | String          | Mandatory          | The unique identifying name of this integration. Usually kebab case of the Display Name                                                                                                                                  |
| `categories`                | Array of String | Mandatory          | Integration categories used on the public documentation [Integrations][1] page.                                                                                                                                          |
| `creates_events`            | Boolean         | Mandatory          | If the integration should be able to create events. If this is set to `false`, attempting to create an event from the integration results in an error.                                                                   |
| `display_name`              | String          | Mandatory          | The title displayed on the corresponding integration tile on the Datadog site and the [Integrations page][1].                                                                                                            |
| `guid`                      | String          | Mandatory          | Unique ID for the integration. [Generate a UUID][2]                                                                                                                                                                      |
| `is_public`                 | Boolean         | Mandatory          | If set to `false` the integration `README.md` content is not included in the Datadog public documentation.                                                                                                               |
| `maintainer`                | String          | Mandatory          | Email of the owner of the integration.                                                                                                                                                                                   |
| `manifest_version`          | String          | Mandatory          | Version of the current manifest.                                                                                                                                                                                         |
| `name`                      | String          | Mandatory          | Unique name for the integration. Use the folder name for this parameter.                                                                                                                                                 |
| `public_title`              | String          | Mandatory          | Title of the integration displayed on the documentation. Should follow the following format: `<INTEGRATION_NAME>`.                                                                                                       |
| `short_description`         | String          | Mandatory          | This text appears at the top of the integration tile as well as the integration's rollover text on the integrations page. Maximum 80 characters.                                                                         |
| `support`                   | String          | Mandatory          | Owner of the integration.                                                                                                                                                                                                |
| `supported_os`              | Array of String | Mandatory          | List of supported OSs. Choose among `linux`,`mac_os`, and `windows`.                                                                                                                                                     |
| `type`                      | String          | Mandatory          | Type of the integration, should be set to `check`.                                                                                                                                                                       |
| `aliases`                   | Array of String | Optional           | A list of URL aliases for the Datadog documentation.                                                                                                                                                                     |
| `description`               | String          | Optional           | This text appears when sharing an integration documentation link.                                                                                                                                                        |
| `is_beta`                   | Boolean         | Optional           | Default `false`. If set to `true` the integration `README.md` content is not displayed in the Datadog public documentation.                                                                                              |
| `metric_to_check`           | String          | Optional           | The presence of this metric determines if this integration is working properly. If this metric is not being reported when this integration is installed, the integration is marked as broken on the Datadog site.        |
| `metric_prefix`             | String          | Optional           | The namespace for this integration's metrics. Every metric reported by this integration is prepended with this value.                                                                                                    |
| `process_signatures`        | Array of String | Optional           | A list of signatures that matches the command line of this integration.                                                                                                                                                  |
| `assets`                    | Dictionary      | Mandatory          | Relative location of where certain asset files live and their respective names.                                                                                                                                          |
| `assets`-> `dashboards`     | Dictionary      | Mandatory          | Dictionary where the key is the name of the dashboard (must be globally unique across integrations) and the value is the relative file path where the dashboard definition lives.                                        |
| `assets`-> `monitors`       | Dictionary      | Mandatory          | Dictionary where the key is the name of the monitor (must be globally unique across integrations) and the value is the relative file path where the dashboard definition lives.                                          |
| `assets`-> `service_checks` | String          | Mandatory          | Relative location of where the `service_checks.json` file lives.                                                                                                                                                         |

[1]: https://docs.datadoghq.com/integrations/
[2]: https://www.uuidgenerator.net


{{% /tab %}}
{{< /tabs >}}


## Service check file

The `service_check.json` file describes the service checks made by the integration.

The `service_checks.json` file contains the following mandatory attributes:

| Attribute       | Description                                                                                                                |
| --------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `agent_version` | Minimum Agent version supported.                                                                                           |
| `integration`   | The name of the integration that emits this service check. Must be the non-normalized `display_name` from `manifest.json`. |
| `check`         | Name of the Service Check. It must be unique.                                                                              |
| `statuses`      | List of different status of the check, to choose among `ok`, `warning`, and `critical`. `unknown` is also a possibility.   |
| `groups`        | [Tags][8] sent with the Service Check.                                                                                     |
| `name`          | Displayed name of the Service Check. The displayed name must be self-explanatory and unique across all integrations.       |
| `description`   | Description of the Service Check                                                                                           |


## Metrics metadata file

The `metadata.csv` file describes all of the metrics that can be collected by the integration.

Descriptions of each column of the `metadata.csv` file:

| Column name     | Mandatory/Optional | Description                                                                                                                                                                                                                                                                                                                             |
| --------------- | ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `metric_name`   | Mandatory          | Name of the metric.                                                                                                                                                                                                                                                                                                                     |
| `metric_type`   | Mandatory          | [Type of the metric][6].                                                                                                                                                                                                                                                                                                                |
| `interval`      | Optional           | Collection interval of the metric in second.                                                                                                                                                                                                                                                                                            |
| `unit_name`     | Optional           | Unit of the metric. [Complete list of supported units][7].                                                                                                                                                                                                                                                                              |
| `per_unit_name` | Optional           | If there is a unit sub-division, i.e `request per second`                                                                                                                                                                                                                                                                               |
| `description`   | Optional           | Description of the metric.                                                                                                                                                                                                                                                                                                              |
| `orientation`   | Mandatory          | Set to `1` if the metric should go up, i.e `myapp.turnover`. Set to `0` if the metric variations are irrelevant. Set to `-1` if the metric should go down, i.e `myapp.latency`.                                                                                                                                                         |
| `integration`   | Mandatory          | The name of the integration that emits the metric. Must be the normalized version of the `display_name` from the `manifest.json` file. Any character besides letters, underscores, dashes, and numbers are converted to underscores, for example: `Openstack Controller` -> `openstack_controller`and `ASP.NET` -> `asp_net` and `CRI-o` -> `cri-o`. |
| `short_name`    | Mandatory          | Explicit Unique ID for the metric.                                                                                                                                                                                                                                                                                                      |
| `curated_metric`| Optional           | Marks the metric as noteworthy for a given type (`cpu` and `memory` are both accepted types).


[1]: https://github.com/DataDog/documentation/blob/master/CONTRIBUTING.md
[2]: https://en.wikipedia.org/wiki/YAML
[3]: http://yaml-online-parser.appspot.com/
[4]: https://docs.datadoghq.com/integrations/
[5]: https://www.uuidgenerator.net
[6]: https://docs.datadoghq.com/developers/metrics/metrics_type/
[7]: https://docs.datadoghq.com/developers/metrics/metrics_units/
[8]: https://docs.datadoghq.com/getting_started/tagging/
[9]: https://docs.datadoghq.com/developers/marketplace/
[10]: https://docs.datadoghq.com/developers/datadog_apps/
