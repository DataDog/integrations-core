# Documentation specification

!!! warning
    This page is an in-progress specification of functionality that has not been implemented yet.

-----

Building on top of the [configuration spec](config-specs.md) implementation, we also incorporate a documentation spec.

Similar to configuration specs, these YAML files are located at `<INTEGRATION>/assets/documentation/spec.yaml`, and referenced in the check's `manifest.json` file.

## Producer

The [producer](#TODO)'s job is to read a specification and:

1. Validate for correctness
1. Populate all unset default fields
1. Gather and prioritize other schema for inclusion
1. Resolve any defined templates
1. Normalize links to embedded style
1. Output the complete specification as JSON for arbitrary consumers

This spec is dependent on other config files within an integration check, in order of precedence:

- `manifest.json`
- `assets/service_checks.json`
- `assets/configuration/spec.yaml` (included for reference, but unused for now)

## Consumers

Consumers may utilize specs in a number of scenarios, such as:

- rendering [README.md](#readme-file-consumer) files for git and user documentation
- rendering HTML files for user documentation on our datadoghq.com site
- easily updating common components via base template changes
- creating single-source-of-truth for data such as `short_description`

## Schema

The root of every spec is a map with 3 keys:

- `name` - The display name of what the spec refers to e.g. `Postgres`, `Nagios`, etc.
- `version` - The released version of what the spec refers to
- `options` - Top-level [spec options](#spec-options) related to the check overall (optional)
- `files` - A list of all [files](#files) that influence behavior

### Spec Options

Every spec has a set of optional options:

- `autodiscovery` - Indicates if this check supports autodiscovery.  Default: false

### Files

Every file has 3 possible attributes:

- `name` - This is the name of the file the Agent will look for (**REQUIRED**)
- `render_name` - This is the name of the rendered file, and defaults to `README.md`.
  Consumers may choose their own output name, or may read from this value.
- `sections` - A list of [sections](#sections) (**REQUIRED**)

### Sections

Every section has these possible attributes:

- `name` - The title of the section.
- `header_level` - Level of indentation.
- `tab` - If not null, then the name of the tab, and all sections of the same indent must specify.
- `description` - Actual text content for the section.  May be parameterized using keyword argument formatter
  strings, see [parameterization](#parameters) for more info. Hyperlinks may be embedded or reference-style.
- `parameters` - Mapping of extra parameters for string formatting in the `description`.
- `prepend_text` - Text to insert in front of the description field. Useful for overrides.
- `append_text` - Text to append after the description field. Useful for overrides.
- `processor` - Reference to a Python function which should be invoked.  If the function returns `None`, the default description carries forward, otherwise the results of the function will be used for the `description`.  Used by the `data_collected/service_checks` template, for example.
- `hidden` - Whether or not the section should be publicly exposed. It defaults to `false`.
- `sections` - Nested sections, this will increase the `header_level` of embedded sections accordingly.
- `template` - See [templates](#templates) below for more.
- `overrides` - Override specific attributes within a given template.  See [overrides](#overrides) for more.

#### Parameters

When constructing each text section, the description field will first prepend and append values from `prepend_text` and `append_text`, respectively.  Next string formatting operations will take place by using a default set of parameters joined with any parameters explicitly defined in the `parameter` attribute.

Default parameters which will be present for all sections and passed as keyword args during string formatting include:

- `name` - the formal name of the check
- all fields from `manifest.json`
- objects from `service_checks.json`

## Templates

Every [section](#section) may reference [pre-defined doc templates](#TODO) using a key called `template`.
The template format looks like `path/to/template_file` where `path/to` must point an existing directory relative
to a template directory and `template_file` must have the file extension `.yaml` or `.yml`.

You can use custom templates that will take precedence over the pre-defined templates by using the `template_paths`
parameter of the [ConfigSpec](#datadog_checks.dev.tooling.configuration.core.ConfigSpec) class.

### Overrides

Commonly used to update a description of a given template, or to inject specific parameters:

```yaml
sections:
- template: setup/installation
  overrides:
    description: |
      The Nagios check is included in the [Datadog Agent][1] package,
      so you don't need to install anything else on your Nagios servers.

      [1]: https://docs.datadoghq.com/agent/
```

For occasions when deeply nested default template values need to be overridden, there is the ability to redefine
attributes via a ++period++ (dot) accessor.

```yaml
options:
- template: setup/configuration
  overrides:
    templates.log_collection.hidden: true
```

## README file consumer

The [README example consumer][] uses the documentation spec to render the README files that are included with
every Integration package.

### Links

As a custom with our README.md files, we use [reference style links](https://www.markdownguide.org/basic-syntax/#reference-style-links). Each section description may have embedded or reference style links, and as part of the [Producer](#producer) step, these will be all normalized to embedded links.  This ensures that any consumers can handle them as needed.  For the README consumer, it will translate everything to reference style as part of its output stage.

### Usage

Use the `--sync` flag of the [config validation command](../ddev/cli.md#config_1) to render the README files.

