# Configuration specification

-----

Every integration has a specification detailing all the options that influence behavior.
These YAML files are located at `<INTEGRATION>/assets/configuration/spec.yaml`.

## Producer

The [producer][config-spec-producer]'s job is to read a specification and:

1. Validate for correctness
1. Populate all unset default fields
1. Resolve any defined templates
1. Output the complete specification as JSON for arbitrary consumers

## Consumers

Consumers may utilize specs in a number of scenarios, such as:

- rendering [example configuration](#example-file-consumer) shipped to end users
- documenting all options in-app & on the docs site
- form for creating configuration in multiple formats on Integration tiles
- automatic configuration loading for [Checks](../faq/faq.md#integration-vs-check)
- Agent based and/or in-app validator for user-supplied configuration

## Schema

The root of every spec is a map with 3 keys:

- `name` - The display name of what the spec refers to e.g. `Postgres`, `Datadog Agent`, etc.
- `version` - The released version of what the spec refers to
- `files` - A list of all [files](#files) that influence behavior

### Files

Every file has 3 possible attributes:

- `name` - This is the name of the file the Agent will look for (**REQUIRED**)
- `example_name` - This is the name of the example file the Agent will ship. If none is provided, the
  default will be `conf.yaml.example`. The exception is auto-discovery files, which are also named
  `auto_conf.yaml`.
- `options` - A list of [options](#options) (**REQUIRED**)

### Options

Every option has 10 possible attributes:

- `name` - This is the name of the option (**REQUIRED**)
- `description` - Information about the option (**REQUIRED**)
- `required` - Whether or not the option is required for basic functionality. It defaults to `false`.
- `hidden` - Whether or not the option should not be publicly exposed. It defaults to `false`.
- `display_priority` - An integer representing the relative visual rank the option should take on
  compared to other options when publicly exposed. It defaults to `0`, meaning that every option will
  be displayed in the order defined in the spec.
- `deprecation` - If the option is deprecated, a mapping of relevant information. For example:

    ```yaml
    deprecation:
      Release: 8.0.0
      Migration: |
        do this
        and that
    ```

- `multiple` - Whether or not options may be selected multiple times like `instances` or just once
  like `init_config`
- `metadata_tags` - A list of tags (like `docs:foo`) that can serve for unexpected use cases in the future
- `options` - Nested options, indicating that this is a section like `instances` or `logs`
- `value` - The expected type data

There are 2 types of options: those with and without a `value`. Those with a `value` attribute are the
actual user-controlled settings that influence behavior like `username`. Those without are expected to
be sections and therefore must have an `options` attribute. An option cannot have both attributes.

Options with a `value` (non-section) also support:

- `secret` - Whether or not consumers should treat the option as sensitive information like `password`.
  It defaults to `false`.

??? info
    The option vs section logic was chosen instead of going fully typed to avoid deeply nested `value`s.

### Values

The type system is based on a loose subset of OpenAPI 3 [data types][openapi-data-types].

The differences are:

- Types cannot be mixed e.g. `oneOf` is invalid in all cases
- Only the `minimum` and `maximum` numeric modifiers are supported
- Only the `pattern` string modifier is supported
- The `properties` object modifier is not a map, but rather a list of maps with a required `name`
  attribute. This is so consumers will load objects consistently regardless of language guarantees
  regarding map key order.

Values also support 1 field of our own:

- `example` - An example value, only required if the type is `boolean`. The default is `<OPTION_NAME>`.

## Templates

Every [option](#options) may reference [pre-defined templates][config-spec-templates] using a key called `template`.
The template format looks like `path/to/template_file` where `path/to` must point an existing directory relative
to a template directory and `template_file` must have the file extension `.yaml` or `.yml`.

You can use custom templates that will take precedence over the pre-defined templates by using the `template_paths`
parameter of the [ConfigSpec](#datadog_checks.dev.tooling.configuration.core.ConfigSpec) class.

### Override

For occasions when deeply nested default template values need to be overridden, there is the ability to redefine
attributes via a ++period++ (dot) accessor.

```yaml
options:
- template: instances/http
  overrides:
    timeout.value.example: 42
```

## Example file consumer

The [example consumer][config-spec-example-consumer] uses each spec to render the example configuration files that
are shipped with every Agent and individual Integration release.

It respects a few extra [option](#options)-level attributes:

- `example` - A complete example of a option in lieu of a strictly typed `value` attribute
- `enabled` - Whether or not to un-comment the option, overriding the behavior of `required`

It also respects a few extra fields under the `value` attribute of each option:

- `default` - This is the default value that will be shown in the header of each option, useful if it differs from the `example`.
  You may set it to `null` explicitly to disable showing this part of the header.
- `compact_example` - Whether or not to display complex types like arrays in their most compact representation. It defaults to `false`.

### Usage

Use the `--sync` flag of the [config validation command](../ddev/cli.md#config_1) to render the example configuration files.

## API

::: datadog_checks.dev.tooling.configuration.ConfigSpec
    rendering:
      heading_level: 3
    selection:
      members:
        - __init__
        - load
