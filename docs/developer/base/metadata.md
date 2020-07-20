# Metadata

-----

Often, you will want to collect mostly unstructured data that doesn't map well to tags, like fine-grained
product version information.

The base class provides [a method](api.md#datadog_checks.base.checks.base.AgentCheck.set_metadata) that
handles such cases. The collected data is captured by [flares][datadog-agent-flare], displayed on the
Agent's [status page][datadog-agent-status-page], and will eventually be queryable [in-app][].

## Interface

The `set_metadata` method of the base class updates cached metadata values, which are then
sent by the Agent at regular intervals.

It requires 2 arguments:

1. `name` - The name of the metadata.
2. `value` - The value for the metadata. If `name` has no transformer defined then the raw `value` will be
   submitted and therefore it must be a `str`.

The method also accepts arbitrary keyword arguments that are forwarded to any defined transformers.

## Transformers

::: datadog_checks.base.utils.metadata.MetadataManager
    rendering:
      heading_level: 3
      show_root_heading: false
      show_root_toc_entry: false
    selection:
      members:
        - transform_version
        - transform_config
