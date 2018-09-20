# Fluentd Integration

![Fluentd Dashboard][8]

## Overview

Get metrics from Fluentd to:

* Visualize Fluentd performance.
* Correlate the performance of Fluentd with the rest of your applications.

## Setup
### Installation

The Fluentd check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Fluentd servers.

### Configuration

Edit the `fluentd.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][16] to start collecting your FluentD [metrics](#metric-collection) and [logs](#log-collection).
See the [sample fluentd.d/conf.yaml][2] for all available configuration options.

#### Prepare Fluentd

In your fluentd configuration file, add a `monitor_agent` source:

```
<source>
  @type monitor_agent
  bind 0.0.0.0
  port 24220
</source>
```

#### Metric Collection

1. Add this configuration block to your `fluentd.d/conf.yaml` file to start gathering your [Fluentd metrics](#metrics):

    ```yaml
      init_config:

      instances:
        - monitor_agent_url: http://localhost:24220/api/plugins.json
          #tag_by: "type" # defaults to 'plugin_id'
          #plugin_ids:    # collect metrics only on your chosen plugin_ids (optional)
          #  - plg1
          #  - plg2
    ```

    See the [sample fluentd.d/conf.yaml][2] for all available configuration options.

2. [Restart the Agent][3] to begin sending Fluentd metrics to Datadog.

#### Log Collection

As long as you can forward your FluentD logs over tcp/udp to a specific port, you can use that approach to forward your FluentD logs to your Datadog agent. But another option is to use the [Datadog FluentD plugin][9] to forward the logs directly from FluentD to your Datadog account. 

##### Add metadata to your logs

Proper metadata (including hostname and source) is the key to unlocking the full potential of your logs in Datadog. By default, the hostname and timestamp fields should be properly remapped via the [remapping for reserved attributes][10].

##### Source and Custom tags

Add the `ddsource` attribute with [the name of the log integration][14] in your logs in order to trigger the [integration automatic setup][11] in Datadog.
[Host tags][13] are automatically set on your logs if there is a matching hostname in your [infrastructure list][12]. Use the `ddtags` attribute to add custom tags to your logs:

Setup Example:

```
  # Match events tagged with "datadog.**" and
  # send them to Datadog

<match datadog.**>

  @type datadog
  @id awesome_agent
  api_key <your_api_key>

  # Optional
  include_tag_key true
  tag_key 'tag'

  # Optional tags
  dd_source '<INTEGRATION_NAME>' 
  dd_tags '<KEY1:VALUE1>,<KEY2:VALUE2>'
  dd_sourcecategory '<SOURCE_CATEGORY>'

</match>
```

##### Kubernetes and Docker tags

Datadog tags are critical to be able to jump from one part of the product to another. Having the right metadata associated with your logs is therefore important in jumping from a container view or any container metrics to the most related logs.

If your logs contain any of the following attributes, these attributes are automatically added as Datadog tags on your logs:

* `kubernetes.container_image`
* `kubernetes.container_name`
* `kubernetes.namespace_name`
* `kubernetes.pod_name`
* `docker.container_id`

While the Datadog Agent collects Docker and Kubernetes metadata automatically, FluentD requires a plugin for this. We recommend using [fluent-plugin-kubernetes_metadata_filter][15] to collect this metadata.

Configuration example:

```
# Collect metadata for logs tagged with "kubernetes.**"
 <filter kubernetes.*>
   type kubernetes_metadata
 </filter>
```


### Validation

[Run the Agent's `status` subcommand][4] and look for `fluentd` under the Checks section.

## Data Collected
### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

### Events
The FluentD check does not include any events at this time.

### Service Checks

`fluentd.is_ok`:

Returns 'Critical' if the Agent cannot connect to Fluentd to collect metrics. This is the check which most other integrations would call `can_connect`.

## Troubleshooting
Need help? Contact [Datadog Support][6].

## Further Reading

* [How to monitor Fluentd with Datadog][7]

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/fluentd/datadog_checks/fluentd/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/fluentd/metadata.csv
[6]: https://docs.datadoghq.com/help/
[7]: https://www.datadoghq.com/blog/monitor-fluentd-datadog/
[8]: https://raw.githubusercontent.com/DataDog/integrations-core/master/fluentd/images/snapshot-fluentd.png
[9]: http://www.rubydoc.info/gems/fluent-plugin-datadog/
[10]: https://docs.datadoghq.com/logs/processing/#edit-reserved-attributes
[11]: https://docs.datadoghq.com/logs/processing/#integration-pipelines
[12]: https://app.datadoghq.com/infrastructure
[13]: https://docs.datadoghq.com/getting_started/tagging/assigning_tags/
[14]: https://docs.datadoghq.com/integrations/#cat-log-collection
[15]: https://github.com/fabric8io/fluent-plugin-kubernetes_metadata_filter
[16]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
