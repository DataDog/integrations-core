---
title: Integration Assets Reference
kind: documentation
description: Learn about the various assets that need to be included when preparing a Datadog integration.
further_reading:
  - link: "https://github.com/DataDog/documentation/blob/master/CONTRIBUTING.md"
    tag: "GitHub"
    text: "Contributing Guidelines for the Documentation Site"
  - link: "/developers/integrations/"
    tag: "Documentation"
    text: "Learn about creating an Agent or API-based integration"
  - link: "/developers/integrations/oauth_for_integrations/"
    tag: "Documentation"
    text: "Learn about using OAuth for integrations"
---

## Overview

This page walks you through how to develop an offering on the [**Integrations** page][12] or the [**Marketplace** page][9]. 

## Configuration file

When preparing a new integration, you must include an example configuration that contains the necessary options and reasonable defaults. The example configuration file—which in this case, is located at `<CHECK_NAME>/datadog_checks/<CHECK_NAME>/data/conf.yaml.example`—has two top-level elements: `init_config` and `instances`. 

The configuration under `init_config` is applied to the integration globally, and is used in every instantiation of the integration, whereas anything within `instances` is specific to a given instantiation.

Configuration blocks in either section take the following form:

```yaml
## @<COMMAND> [- <ARGS>]
## <DESCRIPTION LINE 1>
## <DESCRIPTION LINE 2>
#
<KEY>: <VALUE>
```

Configuration blocks follow a few guidelines:

- Descriptions must not be empty.
- Always follow this format: `<THIS_IS_A_PLACEHOLDER>` for placeholders. For more information, see the [Documentation Site's contributing guidelines][1].
- All required parameters are **not** commented by default.
- All optional parameters are commented by default.
- If a placeholder has a default value for an integration (like the status endpoint of an integration), it can be used instead of a generic placeholder.

### `@param` specification

You can use the `@param` command to describe configuration blocks and provide documentation for your configuration. 

`@param` is implemented using one of the following forms:

```text
@param <name> - <type> - required
@param <name> - <type> - optional
@param <name> - <type> - optional - default: <defval>
```

**Arguments**:

- `name`: The name of the parameter, such as `search_string` (mandatory).
- `type`: The data type for the parameter value (mandatory).
          Possible values include the following: _boolean_, _string_, _integer_, _double_, _float_, _dictionary_, _list\*_, and _object\*_.
- `defval`: Default value for the parameter; can be empty (optional).

`list` and `object` variables span over multiple lines and have special rules.

- In a `list`, individual elements are not documented with the `@param` specification.
- In an `object`, you can choose to either document elements individually with the `@param` specification or have a common top-level description following the specification of the object itself.

### Optional parameters

An optional parameter must be commented by default. Before every line the parameter spans on, add `#` with the same indentation as the `@param` specification.

### Block comments

You can add a block comment anywhere in the configuration file with the following rules:

- Comments start with `##`.
- Comments should be indented like any variable (the hyphen doesn't count).

For more information about YAML syntax, see the [Wikipedia article about YAML][2]. You can also explore the [Online YAML Parser][3].

## Manifest file

Every offering on the [**Integrations** page][4] or the [**Marketplace** page][11] contains a `manifest.json` file that defines operating parameters, positioning within the greater Datadog integration ecosystem, and additional metadata.

{{% integration-assets-reference %}}

### Classifier tags

You can set multiple categories and define submitted or queried data types for the integration using the `classifier_tags` parameter.

You can find the complete list of classifier tags for the `manifest.json` file below: 

{{% integration_categories %}}

## Service check file

The `service_check.json` file describes the service checks made by the integration.

You can find the complete list of mandatory attributes for the `service_checks.json` file below: 

| Attribute       | Description                                                                                                                |
| --------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `agent_version` | Minimum Agent version supported.                                                                                           |
| `integration`   | The name of the integration that emits this service check. Must be the non-normalized `display_name` from `manifest.json`. |
| `check`         | Name of the service check. It must be unique.                                                                              |
| `statuses`      | List of different status of the check, to choose among `ok`, `warning`, and `critical`. `unknown` is also a possibility.   |
| `groups`        | [Tags][8] sent with the service check.                                                                                     |
| `name`          | Displayed name of the service check. The displayed name must be self-explanatory and unique across all integrations.       |
| `description`   | Description of the service check.                                                                                           |


## Metrics metadata file

The `metadata.csv` file describes all of the metrics that can be collected by the integration.

You can find the complete list of mandatory and optional attributes for the `metadata.csv` file below: 

| Column name     | Mandatory or Optional | Description                                                                                                                                                                                                                                                                                                                             |
| --------------- | ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `metric_name`   | Mandatory          | Name of the metric.                                                                                                                                                                                                                                                                                                                     |
| `metric_type`   | Mandatory          | Type of the metric. For a list of available metric submission types, see [Metrics Types][6].                                                                                                                                                                                                                                                                                                                |
| `interval`      | Optional           | Collection interval of the metric in seconds.                                                                                                                                                                                                                                                                                            |
| `unit_name`     | Optional           | Unit of the metric. For a complete list of supported units, see [Metrics Units][7].                                                                                                                                                                                                                                                                              |
| `per_unit_name` | Optional           | If there is a unit sub-division, such as `request per second`.                                                                                                                                                                                                                                                                               |
| `description`   | Optional           | Description of the metric.                                                                                                                                                                                                                                                                                                              |
| `orientation`   | Mandatory          | Set to `1` if the metric should go up, such as `myapp.turnover`. Set to `0` if the metric variations are irrelevant. Set to `-1` if the metric should go down, such as `myapp.latency`.                                                                                                                                                         |
| `integration`   | Mandatory          | The name of the integration that emits the metric. Must be the normalized version of the `display_name` from the `manifest.json` file. Any character besides letters, underscores, dashes, and numbers are converted to underscores. For example: `Openstack Controller` -> `openstack_controller`, `ASP.NET` -> `asp_net`, and `CRI-o` -> `cri-o`. |
| `short_name`    | Mandatory          | Explicit unique ID for the metric.                                                                                                                                                                                                                                                                                                      |
| `curated_metric`| Optional           | Marks which metrics for an integration are noteworthy for a given type (`cpu` and `memory` are both accepted). These are displayed in the UI above the other integration metrics.

## Further Reading

{{< partial name="whats-next/whats-next.html" >}}

[1]: https://github.com/DataDog/documentation/blob/master/CONTRIBUTING.md#code-substitution
[2]: https://en.wikipedia.org/wiki/YAML
[3]: http://yaml-online-parser.appspot.com/
[4]: https://docs.datadoghq.com/integrations/
[5]: https://www.uuidgenerator.net
[6]: https://docs.datadoghq.com/metrics/types/#metric-types
[7]: https://docs.datadoghq.com/metrics/units/#unit-list
[8]: https://docs.datadoghq.com/getting_started/tagging/
[9]: https://app.datadoghq.com/marketplace/
[10]: https://docs.datadoghq.com/developers/datadog_apps/
[11]: https://docs.datadoghq.com/developers/integrations/marketplace_offering
[12]: https://app.datadoghq.com/integrations