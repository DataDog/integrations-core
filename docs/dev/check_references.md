---
title: Integration assets reference
kind: documentation
---

## Configuration file

When preparing a new integration, you must include an example configuration that contains the necessary options and reasonable defaults. The example configuration file, which in this case is located at `awesome/datadog_checks/awesome/data/conf.yaml.example`, has two top-level elements: `init_config` and `instances`. The configuration under `init_config` is applied to the integration globally, and is used in every instantiation of the integration, whereas anything within `instances` is specific to a given instantiation.

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

### @param specification

Practically speaking, the only command is `@param`, which is used to describe configuration blocks—primarily for documentation purposes. `@param` is implemented using one of the following forms:

```text
@param <name> - <type> - required
@param <name> - <type> - optional
@param <name> - <type> - optional - default: <defval>
```

Arguments:

- `name`: the name of the parameter, e.g. `search_string` (mandatory).
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

An optional parameter must be commented by default. Before every line the parameter spans on, add `#` (note the space) with the same indentation as the `@param` specification.

### Block comments

You can add a block comment anywhere in the configuration file with the following rules:

- Comments start with `##` (note the space)
- Comments should be indented like any variable (the hyphen doesn't count)

For more information about YAML syntax, see [Wikipedia][2]. Feel free to play around with the [Online YAML Parser][3], too!

## Manifest file

Every integration contains a `manifest.json` file that describes operating parameters, positioning within the greater Datadog integration eco-system, and other such items.

The complete list of mandatory and optional attributes for the `manifest.json` file:

| Attribute                   | Type            | Mandatory/Optional | Description                                                                                                                                                                                                              |
| --------------------------- | --------------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `integration_id`            | String          | Mandatory          | The unique identifying name of this integration. Usually kebab case of the Display Name                                                                                                                                  |
| `categories`                | Array of String | Mandatory          | Integration categories used on the [public documentation integrations page][4].                                                                                                                                          |
| `creates_events`            | Boolean         | Mandatory          | If the integration should be able to create events. If this is set to `false`, attempting to create an event from the integration results in an error.                                                                   |
| `display_name`              | String          | Mandatory          | Title displayed on the corresponding integration tile in the Datadog application and on the [public documentation integrations page][4]                                                                                  |
| `guid`                      | String          | Mandatory          | Unique ID for the integration. [Generate a UUID][5]                                                                                                                                                                      |
| `is_public`                 | Boolean         | Mandatory          | If set to `false` the integration `README.md` content is not indexed by bots in the Datadog public documentation.                                                                                                        |
| `maintainer`                | String          | Mandatory          | Email of the owner of the integration.                                                                                                                                                                                   |
| `manifest_version`          | String          | Mandatory          | Version of the current manifest.                                                                                                                                                                                         |
| `name`                      | String          | Mandatory          | Unique name for the integration. Use the folder name for this parameter.                                                                                                                                                 |
| `public_title`              | String          | Mandatory          | Title of the integration displayed on the documentation. Should follow the following format: `Datadog-<INTEGRATION_NAME> integration`.                                                                                   |
| `short_description`         | String          | Mandatory          | This text appears at the top of the integration tile as well as the integration's rollover text on the integrations page. Maximum 80 characters.                                                                         |
| `support`                   | String          | Mandatory          | Owner of the integration.                                                                                                                                                                                                |
| `supported_os`              | Array of String | Mandatory          | List of supported OSs. Choose among `linux`,`mac_os`, and `windows`.                                                                                                                                                     |
| `type`                      | String          | Mandatory          | Type of the integration, should be set to `check`.                                                                                                                                                                       |
| `aliases`                   | Array of String | Optional           | A list of URL aliases for the Datadog documentation.                                                                                                                                                                     |
| `description`               | String          | Optional           | This text appears when sharing an integration documentation link.                                                                                                                                                        |
| `is_beta`                   | Boolean         | Optional           | Default `false`. If set to `true` the integration `README.md` content is not displayed in the Datadog public documentation.                                                                                              |
| `metric_to_check`           | String          | Optional           | The presence of this metric determines if this integration is working properly. If this metric is not being reported when this integration is installed, the integration is marked as broken in the Datadog application. |
| `metric_prefix`             | String          | Optional           | The namespace for this integration's metrics. Every metric reported by this integration will be prepended with this value.                                                                                               |
| `process_signatures`        | Array of String | Optional           | A list of signatures that matches the command line of this integration.                                                                                                                                                  |
| `assets`                    | Dictionary      | Mandatory          | Relative location of where certain asset files live and their respective names.                                                                                                                                          |
| `assets`-> `dashboards`     | Dictionary      | Mandatory          | Dictionary where the key is the name of the dashboard (must be globally unique across integrations) and the value is the relative file path where the dashboard definition lives.                                        |
| `assets`-> `monitors`       | Dictionary      | Mandatory          | Dictionary where the key is the name of the monitor (must be globally unique across integrations) and the value is the relative file path where the dashboard definition lives.                                          |
| `assets`-> `service_checks` | String          | Mandatory          | Relative location of where the `service_checks.json` file lives.                                                                                                                                                         |

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
| `integration`   | Mandatory          | Name of the integration that emits the metric. Must be the normalized version of the `display_name` from the `manifest.json` file. Any character besides letters, underscores, dashes and numbers are converted to underscores. E.g. `Openstack Controller` -> `openstack_controller`and `ASP.NET` -> `asp_net` and `CRI-o` -> `cri-o`. |
| `short_name`    | Mandatory          | Explicit Unique ID for the metric.                                                                                                                                                                                                                                                                                                      |

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

[1]: https://github.com/DataDog/documentation/blob/master/CONTRIBUTING.md
[2]: https://en.wikipedia.org/wiki/YAML
[3]: http://yaml-online-parser.appspot.com/
[4]: https://docs.datadoghq.com/integrations
[5]: https://www.uuidgenerator.net
[6]: https://docs.datadoghq.com/developers/metrics/metrics_type/
[7]: https://docs.datadoghq.com/developers/metrics/metrics_units/
[8]: https://docs.datadoghq.com/getting_started/tagging
